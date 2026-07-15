/**
 * Atlas do Montanhismo Paranaense — GPX contribution backend.
 *
 * A Web App the static atlas (GitHub Pages) posts GPX files to. Files land in a
 * Drive folder and are indexed in a Sheet; doGet serves back only the rows flagged
 * published, so a public write endpoint cannot put anything on the shared map
 * without review. The contributor still sees their own track instantly, because the
 * front-end draws it locally before the network call.
 *
 * Deploy: see README.md in this folder.
 */

/** Drive folder + Sheet are created on first use and remembered in script properties. */
var FOLDER_NAME = 'Serra do Mar WebGIS — GPX enviados';
var SHEET_NAME  = 'Serra do Mar WebGIS — índice de GPX';
var MAX_BYTES   = 8 * 1024 * 1024;
var MAX_LIST    = 60;          // cap what a single list call ships back
var HEADERS     = ['id', 'criado_em', 'nome', 'arquivo', 'km', 'trilhas', 'pontos',
                   'bytes', 'ip_hash', 'publicado', 'file_id'];

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function props_() { return PropertiesService.getScriptProperties(); }

function folder_() {
  var id = props_().getProperty('FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (err) {} }
  var it = DriveApp.getFoldersByName(FOLDER_NAME);
  var f = it.hasNext() ? it.next() : DriveApp.createFolder(FOLDER_NAME);
  props_().setProperty('FOLDER_ID', f.getId());
  return f;
}

function sheet_() {
  var id = props_().getProperty('SHEET_ID');
  var ss;
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (err) {} }
  if (!ss) {
    ss = SpreadsheetApp.create(SHEET_NAME);
    props_().setProperty('SHEET_ID', ss.getId());
    folder_().addFile(DriveApp.getFileById(ss.getId()));
  }
  var sh = ss.getSheets()[0];
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function rows_() {
  var sh = sheet_();
  if (sh.getLastRow() < 2) return [];
  var values = sh.getRange(2, 1, sh.getLastRow() - 1, HEADERS.length).getValues();
  return values.map(function (r) {
    var o = {};
    HEADERS.forEach(function (h, i) { o[h] = r[i]; });
    return o;
  });
}

/** Cheap sanity check: it must look like GPX and carry at least one coordinate. */
function looksLikeGpx_(text) {
  if (!text || text.length > MAX_BYTES) return false;
  if (text.indexOf('<gpx') === -1) return false;
  return /<(trkpt|rtept|wpt)\b[^>]*\blat\s*=/.test(text);
}

function clean_(s, max) {
  // Keep it printable: drop angle brackets and anything below space. Written as a
  // charCode scan on purpose -- an escape here once landed raw control bytes in the
  // file and turned it binary.
  var str = String(s == null ? '' : s), out = '';
  for (var i = 0; i < str.length; i++) {
    var c = str.charCodeAt(i);
    if (c >= 32 && c !== 60 && c !== 62) out += str.charAt(i);
  }
  return out.trim().slice(0, max || 120);
}

/**
 * GET ?action=list  -> published contributions, with their GPX text
 * GET ?action=ping  -> health check
 */
function doGet(e) {
  var action = (e && e.parameter && e.parameter.action) || 'list';
  try {
    if (action === 'ping') return json_({ ok: true, pong: true });
    if (action !== 'list') return json_({ ok: false, error: 'ação desconhecida' });

    var published = rows_().filter(function (r) { return r.publicado === true || r.publicado === 'TRUE'; });
    published = published.slice(-MAX_LIST);
    var items = [];
    published.forEach(function (r) {
      try {
        var f = DriveApp.getFileById(r.file_id);
        items.push({ id: r.id, name: r.nome, km: r.km, created: String(r.criado_em),
                     gpx: f.getBlob().getDataAsString('UTF-8') });
      } catch (err) { /* a row whose file was removed just drops out of the list */ }
    });
    return json_({ ok: true, items: items });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/**
 * POST {filename, name, km, tracks, waypoints, gpx}
 * Sent as text/plain so the browser treats it as a CORS simple request: Apps
 * Script does not answer preflight OPTIONS, so an application/json POST fails.
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) return json_({ ok: false, error: 'corpo vazio' });
    if (e.postData.contents.length > MAX_BYTES * 1.4) return json_({ ok: false, error: 'arquivo grande demais' });

    var body;
    try { body = JSON.parse(e.postData.contents); }
    catch (err) { return json_({ ok: false, error: 'JSON inválido' }); }

    var gpx = body.gpx;
    if (!looksLikeGpx_(gpx)) return json_({ ok: false, error: 'não parece um GPX com coordenadas' });

    var name = clean_(body.name) || 'Sem nome';
    var filename = clean_(body.filename, 80).replace(/[^\w .\-()]/g, '_') || 'trilha.gpx';
    if (!/\.gpx$/i.test(filename)) filename += '.gpx';

    // Serialise: two visitors posting at once must not collide on the sheet.
    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    var id, fileId;
    try {
      id = Utilities.getUuid().slice(0, 8);
      var stamped = id + '__' + filename;
      var file = folder_().createFile(
        Utilities.newBlob(gpx, 'application/gpx+xml', stamped));
      fileId = file.getId();
      sheet_().appendRow([
        id, new Date(), name, filename,
        Number(body.km) || 0, Number(body.tracks) || 0, Number(body.waypoints) || 0,
        gpx.length, '', false, fileId
      ]);
    } finally {
      lock.releaseLock();
    }
    // published stays false: it reaches the shared map only after review.
    return json_({ ok: true, id: id, published: false });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/**
 * Run from the editor to approve everything pending. Or just tick the `publicado`
 * column in the Sheet by hand — doGet reads the column, not this function.
 */
function publishAllPending() {
  var sh = sheet_();
  if (sh.getLastRow() < 2) return;
  var col = HEADERS.indexOf('publicado') + 1;
  var n = sh.getLastRow() - 1;
  var vals = sh.getRange(2, col, n, 1).getValues();
  var changed = 0;
  for (var i = 0; i < n; i++) {
    if (vals[i][0] !== true && vals[i][0] !== 'TRUE') { vals[i][0] = true; changed++; }
  }
  sh.getRange(2, col, n, 1).setValues(vals);
  Logger.log('publicados: ' + changed);
}

/** Run once from the editor to grant the Drive/Sheets scopes and see the URLs. */
function setup() {
  var f = folder_(), sh = sheet_();
  Logger.log('Pasta : ' + f.getUrl());
  Logger.log('Índice: ' + sh.getParent().getUrl());
}
