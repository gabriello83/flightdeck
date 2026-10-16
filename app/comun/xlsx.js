/* Un Excel de verdad (.xlsx), hecho en el navegador y sin ninguna libreria.
 *
 * POR QUE A MANO. La web no carga nada de fuera (CLAUDE.md: un solo origen), asi
 * que no hay SheetJS ni nada parecido. Un .xlsx es un zip con unos pocos XML, y
 * un zip sin comprimir («stored») son cabeceras y un CRC32: cabe en esta hoja.
 *
 *   const blob = XLSX.libro([
 *     { nombre: 'Incidencias',
 *       titulo: ['CENTRO 500 · tarifas', 'Generado el ...'],      // opcional, arriba
 *       columnas: [{ titulo: 'Máquina', ancho: 12 }, { titulo: 'Precio', ancho: 9, euros: true }],
 *       filas: [['24SE1983', 1.2], ...],
 *       rellenar: [3, 4],     // columnas en amarillo, para que las rellene quien lo recibe
 *       marcar: (fila, col) => bool }                              // celda en rojo claro
 *   ]);
 *   XLSX.descarga(blob, 'tarifas.xlsx');
 *
 * Lo prueba app/comun/prueba_pantallas.js: descarga el fichero, lo descomprime y
 * mira que los XML esten y digan lo que tienen que decir.
 */
'use strict';
(function (raiz) {
  const enc = new TextEncoder();

  const TABLA_CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(bytes) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < bytes.length; i++) c = TABLA_CRC[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  /* Un zip sin comprimir. `ficheros`: [[nombre, texto]]. */
  function zip(ficheros) {
    const partes = [], central = [];
    let desplazamiento = 0;
    const d = new Date();
    const hora = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
    const fecha = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    for (const [nombre, texto] of ficheros) {
      const n = enc.encode(nombre), datos = enc.encode(texto), crc = crc32(datos);
      const cab = new DataView(new ArrayBuffer(30));
      cab.setUint32(0, 0x04034b50, true); cab.setUint16(4, 20, true); cab.setUint16(6, 0x0800, true);
      cab.setUint16(8, 0, true); cab.setUint16(10, hora, true); cab.setUint16(12, fecha, true);
      cab.setUint32(14, crc, true); cab.setUint32(18, datos.length, true); cab.setUint32(22, datos.length, true);
      cab.setUint16(26, n.length, true); cab.setUint16(28, 0, true);
      partes.push(new Uint8Array(cab.buffer), n, datos);
      const cd = new DataView(new ArrayBuffer(46));
      cd.setUint32(0, 0x02014b50, true); cd.setUint16(4, 20, true); cd.setUint16(6, 20, true);
      cd.setUint16(8, 0x0800, true); cd.setUint16(10, 0, true); cd.setUint16(12, hora, true);
      cd.setUint16(14, fecha, true); cd.setUint32(16, crc, true); cd.setUint32(20, datos.length, true);
      cd.setUint32(24, datos.length, true); cd.setUint16(28, n.length, true);
      cd.setUint32(42, desplazamiento, true);
      central.push(new Uint8Array(cd.buffer), n);
      desplazamiento += 30 + n.length + datos.length;
    }
    const tamCentral = central.reduce((a, b) => a + b.length, 0);
    const fin = new DataView(new ArrayBuffer(22));
    fin.setUint32(0, 0x06054b50, true);
    fin.setUint16(8, ficheros.length, true); fin.setUint16(10, ficheros.length, true);
    fin.setUint32(12, tamCentral, true); fin.setUint32(16, desplazamiento, true);
    return new Blob([...partes, ...central, new Uint8Array(fin.buffer)],
      { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }

  const xml = s => String(s == null ? '' : s)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
    .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function letra(i) {
    let s = '';
    for (i++; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + (i - 1) % 26) + s;
    return s;
  }

  /* Los estilos, por numero: 0 normal, 1 cabecera, 2 a rellenar, 3 euros,
     4 titulo, 5 euros marcado, 6 texto marcado. */
  const ESTILOS = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00 &quot;€&quot;"/></numFmts>
<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><name val="Calibri"/></font></fonts>
<fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE7E6E1"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2A8"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF8D2CF"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="2"><border/><border><left style="thin"><color rgb="FFBFBFBF"/></left><right style="thin"><color rgb="FFBFBFBF"/></right><top style="thin"><color rgb="FFBFBFBF"/></top><bottom style="thin"><color rgb="FFBFBFBF"/></bottom></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="7">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment wrapText="1" vertical="center"/></xf>
<xf numFmtId="164" fontId="0" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="1" fillId="4" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1"/>
<xf numFmtId="0" fontId="1" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;

  function celda(ref, valor, estilo) {
    const s = estilo ? ` s="${estilo}"` : '';
    if (valor == null || valor === '') return estilo ? `<c r="${ref}"${s}/>` : '';
    if (typeof valor === 'number' && Number.isFinite(valor)) return `<c r="${ref}"${s}><v>${valor}</v></c>`;
    return `<c r="${ref}"${s} t="inlineStr"><is><t xml:space="preserve">${xml(valor)}</t></is></c>`;
  }

  function hoja(h) {
    const filas = [];
    let r = 0;
    for (const t of h.titulo || []) {
      r++;
      filas.push(`<row r="${r}">${celda('A' + r, t, r === 1 ? 4 : 0)}</row>`);
    }
    if ((h.titulo || []).length) r++;            // una fila en blanco
    const cab = ++r;
    filas.push(`<row r="${cab}">` + h.columnas.map((c, i) => celda(letra(i) + cab, c.titulo, 1)).join('') + '</row>');
    const rellenar = new Set(h.rellenar || []);
    for (const f of h.filas) {
      r++;
      filas.push(`<row r="${r}">` + h.columnas.map((c, i) => {
        const marcada = h.marcar && h.marcar(f, i);
        const estilo = rellenar.has(i) ? 2 : marcada ? (c.euros ? 5 : 6) : c.euros ? 3 : 0;
        return celda(letra(i) + r, f[i], estilo);
      }).join('') + '</row>');
    }
    const cols = h.columnas.map((c, i) => `<col min="${i + 1}" max="${i + 1}" width="${c.ancho || 12}" customWidth="1"/>`).join('');
    const ultima = letra(h.columnas.length - 1);
    return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">`
      + `<sheetViews><sheetView workbookViewId="0"><pane ySplit="${cab}" topLeftCell="A${cab + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>`
      + `<cols>${cols}</cols><sheetData>${filas.join('')}</sheetData>`
      + (h.filas.length ? `<autoFilter ref="A${cab}:${ultima}${r}"/>` : '')
      + `</worksheet>`;
  }

  function libro(hojas) {
    const nombres = hojas.map((h, i) => xml(String(h.nombre || `Hoja${i + 1}`).replace(/[\\/?*[\]:]/g, ' ').slice(0, 31)));
    const ficheros = [
      ['[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>`
        + hojas.map((h, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')
        + '</Types>'],
      ['_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`],
      ['xl/workbook.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>`
        + nombres.map((n, i) => `<sheet name="${n}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')
        + '</sheets>'
        + (hojas.some(h => h.filas.length) ? '<definedNames>' + hojas.map((h, i) => {
          if (!h.filas.length) return '';
          const cab = (h.titulo || []).length ? h.titulo.length + 2 : 1;
          return `<definedName name="_xlnm._FilterDatabase" localSheetId="${i}" hidden="1">'${nombres[i].replace(/'/g, "''")}'!$A$${cab}:$${letra(h.columnas.length - 1)}$${cab + h.filas.length}</definedName>`;
        }).join('') + '</definedNames>' : '')
        + '</workbook>'],
      ['xl/_rels/workbook.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
        + hojas.map((h, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')
        + `<Relationship Id="rId${hojas.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
      ['xl/styles.xml', ESTILOS],
      ...hojas.map((h, i) => [`xl/worksheets/sheet${i + 1}.xml`, hoja(h)])
    ];
    return zip(ficheros);
  }

  function descarga(blob, nombre) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  raiz.XLSX = { libro, descarga, _zip: zip, _crc32: crc32 };
})(typeof window !== 'undefined' ? window : globalThis);
