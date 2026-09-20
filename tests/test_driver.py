#!/usr/bin/env python3
"""End-to-end software checks. No printer, sudo, or third-party Python packages."""
# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FILTER = ROOT / os.environ.get("HBPL_FILTER", "build/rastertohbpl1")
SYNTHETIC = "--synthetic" in sys.argv
if SYNTHETIC:
    sys.argv.remove("--synthetic")


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], stderr=subprocess.PIPE,
                          timeout=120, **kwargs)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BUILD)
        self.work = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, mode):
        path = self.work / (mode + ".ras")
        with path.open("wb") as out:
            p = run([BUILD / "raster-fixture", mode], stdout=out)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        return path

    def convert(self, path, ok=True, copies=1):
        hbpl = self.work / "job.hbpl"
        with hbpl.open("wb") as out:
            p = run([FILTER, "1", "user\n@PJL", 'test"title', str(copies), "", path], stdout=out)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            data = hbpl.read_bytes()
            self.assertIn(b'@PJL SET COPIES=1\n', data)
            self.assertNotIn(b'user\n@PJL', data)
            self.assertNotIn(b'test"title', data)
            p = run([BUILD / "decode-hbpl1", hbpl, self.work / "page"], stdout=subprocess.PIPE)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            return p.stdout.decode(), sorted(self.work.glob("page-*.*"), key=lambda p: int(p.stem.split("-")[-1]))
        self.assertNotEqual(p.returncode, 0, "invalid input unexpectedly accepted")
        self.assertIn(b"ERROR:", p.stderr)
        self.assertNotIn(b"AddressSanitizer", p.stderr)
        self.assertNotIn(b"runtime error:", p.stderr)

    def pixel(self, path, x, y):
        with path.open("rb") as f:
            magic = f.readline().strip()
            width, height = map(int, f.readline().split())
            self.assertEqual(f.readline(), b"255\n")
            depth = 3 if magic == b"P6" else 1
            self.assertLess(x, width); self.assertLess(y, height)
            f.seek((y*width+x)*depth, 1)
            return tuple(f.read(depth))

    def test_rgb_a4_cropped_and_padding(self):
        for mode in ["rgb", "a4", "cropped", "padding"]:
            with self.subTest(mode=mode):
                info, pages = self.convert(self.fixture(mode))
                self.assertEqual(len(pages), 1)
                self.assertIn("paper=2" if mode == "a4" else "paper=0", info)
                self.assertEqual(self.pixel(pages[0], 250, 250), (255,0,0))
                self.assertEqual(self.pixel(pages[0], 100, 250), (255,255,255))
                self.assertEqual(self.pixel(pages[0], 455, 455), (255,0,0))
                self.assertEqual(self.pixel(pages[0], 456, 456), (255,255,255))
                self.assertEqual(self.pixel(pages[0], 2000, 50), (255,255,255))

    def test_grayscale_polarity(self):
        _, pages = self.convert(self.fixture("gray"))
        for x in [200,201,250,327,328,454,455]:
            self.assertEqual(self.pixel(pages[0], x, 250), (x-200,))
        self.assertEqual(self.pixel(pages[0], 100, 100), (255,))

    def test_blank_and_final_row(self):
        _, pages = self.convert(self.fixture("blank"))
        for x,y in [(100,100),(2000,3000),(5099,6599),(5103,6599)]:
            self.assertEqual(self.pixel(pages[0],x,y),(255,255,255))

    def test_noise_color_conversion(self):
        _, pages = self.convert(self.fixture("noise"))
        for x,y in [(200,200),(201,201),(250,250),(350,355),(455,455)]:
            n = (x*1664525+y*1013904223) & 0xffffffff
            expected = (n & 255, (n>>9)&255, (n>>19)&255)
            for actual, value in zip(self.pixel(pages[0],x,y),expected):
                self.assertLessEqual(abs(actual-value),1)

    def test_multiple_pages(self):
        _, pages = self.convert(self.fixture("multi"))
        self.assertEqual(len(pages),3)
        for p, color in zip(pages,[(255,0,0),(0,255,0),(0,0,255)]):
            self.assertEqual(self.pixel(p,250,250),color)

    def test_bad_input(self):
        for mode in ["resolution","colorspace","copies","duplex","dimensions","paper","truncated"]:
            with self.subTest(mode=mode): self.convert(self.fixture(mode),ok=False)
        path = self.work / "invalid.ras"
        for data in [b"",b"RaS2",b"not a raster",b"RaS2"+bytes(100)]:
            path.write_bytes(data); self.convert(path,ok=False)
        good = self.fixture("rgb").read_bytes()
        path.write_bytes(good+b"\0"*17)
        self.convert(path,ok=False)

    def test_input_stdin(self):
        with self.fixture("gray").open("rb") as src, (self.work/"stdin.hbpl").open("wb") as out:
            p=run([FILTER,"1","u","t","1",""],stdin=src,stdout=out)
        self.assertEqual(p.returncode,0,p.stderr.decode())

    def test_output_failure(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            p = run([FILTER,"1","u","t","1","",self.fixture("rgb")],stdout=write_fd)
        finally:
            os.close(write_fd)
        self.assertNotEqual(p.returncode,0)
        self.assertIn(b"Cannot write",p.stderr)

    def test_cancellation(self):
        # Supply a header and keep the pipe open so the filter blocks in a read.
        data = self.fixture("rgb").read_bytes()
        with open(os.devnull,"wb") as out:
            p=subprocess.Popen([str(FILTER),"1","u","t","1",""],stdin=subprocess.PIPE,stdout=out,stderr=subprocess.PIPE)
            try:
                p.stdin.write(data[:1800]);p.stdin.flush()
                time.sleep(0.15)
                p.send_signal(signal.SIGTERM)
                p.wait(timeout=5)
                self.assertNotEqual(p.returncode,0)
            finally:
                if p.poll() is None: p.kill();p.wait()
                p.stdin.close();p.stderr.close()

    def test_ppd_and_staging(self):
        p=run([ROOT/"scripts/install.sh","--stage",self.work/"stage"],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        staged=self.work/"stage/Library/Printers/DellC1660wNative/filter/rastertohbpl1"
        ppd=(ROOT/"ppd/Dell-C1660w-Native.ppd").read_text().replace("/Library/Printers/DellC1660wNative/filter/rastertohbpl1",str(staged))
        check=self.work/"staged.ppd";check.write_text(ppd)
        # CUPS requires root ownership after installation; staging is unprivileged.
        self.assertEqual(staged.stat().st_mode & 0o777,0o755)
        self.assertEqual(staged.read_bytes(),(BUILD/"rastertohbpl1").read_bytes())
        p=run(["cupstestppd","-W","filters",check],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stdout.decode()+p.stderr.decode())
        self.assertNotIn(b"Missing",p.stdout)
        for host in ["-bad","host:9100","host/path","bad host","bad;host"]:
            self.assertNotEqual(run([ROOT/"scripts/setup.sh",host],stdout=subprocess.PIPE).returncode,0)

    @unittest.skipIf(SYNTHETIC,"synthetic-only sanitizer run")
    def test_macos_pdf_pipeline(self):
        pdf=self.work/"fixture.pdf"
        p=run([BUILD/"pdf-fixture",pdf],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        landscape_pdf=self.work/"landscape.pdf"
        p=run([BUILD/"pdf-fixture",landscape_pdf,"landscape"],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        cases=[("color",[],1,[1,2,3]),
               ("gray",["ColorModel=Gray","page-ranges=1"],1,[1]),
               ("range",["page-ranges=2"],1,[2]),
               ("a4",["PageSize=A4","page-ranges=1"],1,[1]),
               ("landscape",["fit-to-page","page-ranges=1"],1,[1]),
               ("collated",["Collate=True"],2,[1,2,3,1,2,3]),
               ("uncollated",["Collate=False"],2,[1,1,2,2,3,3])]
        for name,options,copies,expected in cases:
            with self.subTest(case=name):
                for old in self.work.glob("page-*.*"): old.unlink()
                raster=self.work/"pdf.ras"
                args=["/usr/sbin/cupsfilter","-p",ROOT/"ppd/Dell-C1660w-Native.ppd","-m","application/vnd.cups-raster","-n",str(copies)]
                for option in options:args += ["-o",option]
                with raster.open("wb") as out:
                    p=run(args+[landscape_pdf if name=="landscape" else pdf],stdout=out)
                self.assertEqual(p.returncode,0,p.stderr.decode())
                info,pages=self.convert(raster,copies=copies)
                self.assertEqual(len(pages),len(expected),info)
                if name == "landscape":
                    actual=self.pixel(pages[0],4250,700)
                    self.assertGreater(actual[0]-max(actual[1:]),100)
                    self.assertEqual(self.pixel(pages[0],500,700),(255,255,255))
                elif name == "gray":
                    self.assertEqual(pages[0].suffix,".pgm")
                    self.assertLess(self.pixel(pages[0],500,700)[0],230)
                    self.assertEqual(self.pixel(pages[0],2000,50),(255,))
                elif name == "a4":
                    self.assertIn("width=4960 height=7017",info)
                if name not in ["gray","landscape","a4"]:
                    for path,index in zip(pages,expected):
                        actual=self.pixel(path,500,700)
                        # ColorSync may alter numerical values; channel dominance identifies the page.
                        self.assertEqual(actual.index(max(actual)),index-1,(name,actual))
                        self.assertGreater(max(actual)-min(actual),100)

    @unittest.skipIf(SYNTHETIC,"synthetic-only sanitizer run")
    def test_complete_filter_chain(self):
        pdf=self.work/"fixture.pdf"
        p=run([BUILD/"pdf-fixture",pdf],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        ppd=self.work/"local.ppd"
        ppd.write_text((ROOT/"ppd/Dell-C1660w-Native.ppd").read_text().replace(
            "/Library/Printers/DellC1660wNative/filter/rastertohbpl1",str(FILTER)))
        hbpl=self.work/"chain.hbpl"
        with hbpl.open("wb") as out:
            p=run(["/usr/sbin/cupsfilter","-p",ppd,"-e","-m","printer/test",
                   "-o","page-ranges=2",pdf],stdout=out)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        p=run([BUILD/"decode-hbpl1",hbpl,self.work/"chain"],stdout=subprocess.PIPE)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        self.assertEqual(len(list(self.work.glob("chain-*.ppm"))),1)
        pixel=self.pixel(self.work/"chain-1.ppm",500,700)
        self.assertGreater(pixel[1]-max(pixel[0],pixel[2]),100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
