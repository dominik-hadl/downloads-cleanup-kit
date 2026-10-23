// Print the text of the first pages of a PDF using macOS PDFKit (no extra tools needed).
// usage: osascript -l JavaScript pdftext.js <file.pdf> [pages, default 3]
ObjC.import('PDFKit');
function run(argv) {
  const d = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[0]));
  if (!d || d.isNil()) return '';
  const n = Math.min(d.pageCount, parseInt(argv[1] || '3', 10)); let s = '';
  for (let i = 0; i < n; i++) { const p = d.pageAtIndex(i); if (p && !p.isNil() && !p.string.isNil()) s += p.string.js + '\n'; }
  return s;
}
