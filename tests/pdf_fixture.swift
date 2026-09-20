// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation
import CoreGraphics
import CoreText

let url = URL(fileURLWithPath: CommandLine.arguments[1]) as CFURL
let landscape = CommandLine.arguments.count > 2 && CommandLine.arguments[2] == "landscape"
var page = CGRect(x: 0, y: 0, width: landscape ? 792 : 612, height: landscape ? 612 : 792)
let pdf = CGContext(url, mediaBox: &page, nil)!
for index in 0..<3 {
    pdf.beginPDFPage(nil)
    pdf.setFillColor(CGColor(gray: 1, alpha: 1))
    pdf.fill(page)
    let color = [CGColor(red: 1, green: 0, blue: 0, alpha: 1),
                 CGColor(red: 0, green: 1, blue: 0, alpha: 1),
                 CGColor(red: 0, green: 0, blue: 1, alpha: 1)][index]
    pdf.setFillColor(color)
    pdf.fill(CGRect(x: 36, y: page.height-132, width: 100, height: 80))
    let text = NSAttributedString(string: "Dell C1660w native driver — page \(index+1)",
        attributes: [NSAttributedString.Key(kCTFontAttributeName as String): CTFontCreateWithName("Helvetica" as CFString, 18, nil),
                     NSAttributedString.Key(kCTForegroundColorAttributeName as String): CGColor(gray: 0, alpha: 1)])
    pdf.textPosition = CGPoint(x: 36, y: 620)
    CTLineDraw(CTLineCreateWithAttributedString(text), pdf)
    pdf.saveGState()
    pdf.clip(to: CGRect(x: 36, y: 560, width: 400, height: 30))
    let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
                              colors: [CGColor(gray: 0, alpha: 1), CGColor(gray: 1, alpha: 1)] as CFArray,
                              locations: [0,1])!
    pdf.drawLinearGradient(gradient, start: CGPoint(x: 36,y:560), end: CGPoint(x:436,y:560), options: [])
    pdf.restoreGState()
    // Deterministic continuous-tone image exercises the image path without external assets.
    var pixels = [UInt8](repeating: 0, count: 128*128*3)
    for y in 0..<128 { for x in 0..<128 {
        pixels[(y*128+x)*3] = UInt8(x*2)
        pixels[(y*128+x)*3+1] = UInt8(y*2)
        pixels[(y*128+x)*3+2] = UInt8((x+y)%128*2)
    }}
    let data = Data(pixels) as CFData
    let image = CGImage(width:128,height:128,bitsPerComponent:8,bitsPerPixel:24,bytesPerRow:384,
                        space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGBitmapInfo(rawValue:0),
                        provider:CGDataProvider(data:data)!,decode:nil,shouldInterpolate:true,intent:.defaultIntent)!
    pdf.draw(image,in:CGRect(x:36,y:360,width:128,height:128))
    pdf.setStrokeColor(CGColor(gray:0,alpha:1));pdf.setLineWidth(0.25)
    pdf.stroke(CGRect(x:12,y:12,width:588,height:768))
    pdf.endPDFPage()
}
pdf.closePDF()
