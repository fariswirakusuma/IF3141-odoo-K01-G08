#!/usr/bin/env node
/* Bangun docs/Tabel-Screen-Mockup-Pilar.docx dari docs/screen-mockup-data.json.
 * Jalankan: NODE_PATH=<path node_modules docx> node scripts/build_screen_mockup_docx.js
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, ImageRun, BorderStyle,
  HeadingLevel, VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const data = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/screen-mockup-data.json"), "utf8"));
const screens = data.screens;
const usecases = data.usecases;
const byLetter = Object.fromEntries(screens.map((s) => [s.letter, s]));

const NAVY = "0B2545";
const BORDER = "7F8C9A";
const TABLE_WIDTH = 9400;
const LABEL_WIDTH = 2000;
const CONTENT_WIDTH = TABLE_WIDTH - LABEL_WIDTH;

function pngSize(buffer) {
  if (buffer.toString("ascii", 1, 4) !== "PNG") {
    throw new Error("Bukan berkas PNG");
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

const BORDER_SET = {
  top: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
  left: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
  right: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
  insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
  insideVertical: { style: BorderStyle.SINGLE, size: 4, color: BORDER },
};

function labelCell(text) {
  return new TableCell({
    width: { size: LABEL_WIDTH, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: NAVY, color: "auto" },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 90, bottom: 90, left: 120, right: 120 },
    children: [new Paragraph({
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 22 })],
    })],
  });
}

function contentCell(children) {
  return new TableCell({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    margins: { top: 90, bottom: 90, left: 140, right: 140 },
    children,
  });
}

function textParagraph(text, options = {}) {
  return new Paragraph({
    spacing: { before: 0, after: 0 },
    ...options,
    children: [new TextRun({ text, size: 22, ...options.run })],
  });
}

function screenTable(screen) {
  const imagePath = path.join(ROOT, "docs/screenshots", screen.file);
  const image = fs.readFileSync(imagePath);
  const size = pngSize(image);
  const targetWidth = 488;
  const targetHeight = Math.round((size.height * targetWidth) / size.width);

  return new Table({
    width: { size: TABLE_WIDTH, type: WidthType.DXA },
    columnWidths: [LABEL_WIDTH, CONTENT_WIDTH],
    borders: BORDER_SET,
    rows: [
      new TableRow({ cantSplit: true, children: [
        labelCell("Nama Layar"),
        contentCell([textParagraph(`Layar ${screen.letter} — ${screen.name}`, { run: { bold: true } })]),
      ]}),
      new TableRow({ cantSplit: true, children: [
        labelCell("Deskripsi Layar"),
        contentCell([textParagraph(screen.description)]),
      ]}),
      new TableRow({ cantSplit: true, children: [
        labelCell("User"),
        contentCell([textParagraph(screen.users)]),
      ]}),
      new TableRow({ cantSplit: true, children: [
        labelCell("Tampilan Layar"),
        contentCell([new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 60, after: 60 },
          children: [new ImageRun({
            type: "png",
            data: image,
            transformation: { width: targetWidth, height: targetHeight },
          })],
        })]),
      ]}),
    ],
  });
}

function mappingTable() {
  const header = (text, width, alignment) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: NAVY, color: "auto" },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 90, bottom: 90, left: 100, right: 100 },
    children: [new Paragraph({
      alignment,
      spacing: { before: 0, after: 0, line: 220 },
      children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 20 })],
    })],
  });

  const bodyCell = (children, width, alignment) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    verticalAlign: VerticalAlign.TOP,
    margins: { top: 45, bottom: 45, left: 100, right: 100 },
    children,
  });

  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: [
    header("No", 800, AlignmentType.CENTER),
    header("Use Case / Activity", 4100, AlignmentType.LEFT),
    header("Layar", 4300, AlignmentType.LEFT),
  ]})];

  for (const usecase of usecases) {
    const mapped = usecase.screens.map((letter) => {
      const screen = byLetter[letter];
      return new Paragraph({
        spacing: { before: 0, after: 10, line: 220 },
        children: [new TextRun({ text: `${letter}. Layar ${screen.name}`, size: 19 })],
      });
    });
    rows.push(new TableRow({ cantSplit: true, children: [
      bodyCell([textParagraph(usecase.no, { alignment: AlignmentType.CENTER, run: { size: 19 } })], 800, AlignmentType.CENTER),
      bodyCell([textParagraph(usecase.name, { run: { size: 19 } })], 4100, AlignmentType.LEFT),
      bodyCell(mapped, 4300, AlignmentType.LEFT),
    ]}));
  }

  return new Table({
    width: { size: TABLE_WIDTH, type: WidthType.DXA },
    columnWidths: [800, 4100, 4500],
    borders: BORDER_SET,
    rows,
  });
}

const children = [
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 0, after: 120 },
    children: [new TextRun({ text: "I.7  User Interface", bold: true })],
  }),
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 180, after: 120 },
    children: [new TextRun({ text: "I.7.1  Screen Mockup", bold: true })],
  }),
  new Paragraph({
    spacing: { after: 180, line: 276 },
    children: [new TextRun({
      text: "Spesifikasi layar pada sistem yang akan dibangun disusun berdasarkan implementasi pada Odoo 17. Sesuai ketentuan pada I.7.1, digunakan Opsi 2: screenshot langsung hasil tampilan di Odoo 17. Seluruh gambar diambil dari aplikasi yang berjalan pada http://localhost:8069 dengan data demo; tidak ada tautan Figma karena tidak menggunakan Figma.",
      size: 22,
    })],
  }),
];

screens.forEach((screen, index) => {
  children.push(new Paragraph({
    keepNext: true,
    pageBreakBefore: index > 0,
    spacing: { before: index > 0 ? 0 : 120, after: 100 },
    children: [new TextRun({
      text: `Tabel 1.7.${screen.no} Tabel Screen Mockup Layar ${screen.letter} — ${screen.name}`,
      bold: true,
      size: 21,
    })],
  }));
  children.push(screenTable(screen));
  children.push(new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: "" })] }));
});

children.push(new Paragraph({
  heading: HeadingLevel.HEADING_2,
  pageBreakBefore: true,
  spacing: { before: 0, after: 120 },
  children: [new TextRun({ text: "I.7.2  Pemetaan Layar", bold: true })],
}));
children.push(new Paragraph({
  spacing: { after: 140, line: 276 },
  children: [new TextRun({
    text: "Petakan use case sistem ke dalam layar/tampilan mockup yang telah dibuat.",
    size: 22,
  })],
}));
children.push(new Paragraph({
  keepNext: true,
  spacing: { before: 60, after: 100 },
  children: [new TextRun({ text: "Tabel 1.8 Tabel Pemetaan Layar", bold: true, size: 21 })],
}));
children.push(mappingTable());

const doc = new Document({
  creator: "Kelompok 08 - K01",
  title: "I.7 User Interface — Screen Mockup Modul Validasi dan Persetujuan PO",
  description: "Spesifikasi layar dan pemetaan use case mockup Odoo 17",
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: 22 } },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 28, bold: true, color: "000000" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 24, bold: true, color: "000000" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
      },
    },
    children,
  }],
});

const out = path.join(ROOT, "docs/Tabel-Screen-Mockup-Pilar.docx");
Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(out, buffer);
  console.log(`${out} dibuat (${(buffer.length / 1024).toFixed(0)} KB)`);
});
