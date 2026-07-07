#!/usr/bin/env node
/**
 * verify_bundle.js
 * -------------------
 * Zero-dependency Node.js verifier for the evidence bundles produced by
 * forensic-reporting/evidence_packaging.py.
 *
 * Why this exists: a case owner, auditor, or legal reviewer who receives an
 * evidence bundle should not have to install Python/this toolkit just to
 * confirm the SHA-256 manifest still matches every file inside the ZIP. This
 * gives them a single-file, dependency-free (only Node.js built-ins: fs,
 * zlib, crypto) way to do that independently of the toolkit that produced
 * the bundle -- an independent verifier is a meaningfully stronger integrity
 * check than reusing the same code that wrote the file.
 *
 * Implements just enough of the PKZIP format (End Of Central Directory +
 * Central Directory + Local File Header, STORE and DEFLATE methods) to read
 * the files Python's `zipfile` module writes. Not a general-purpose ZIP
 * library -- see README in this directory for scope.
 *
 * Usage:
 *   node verify_bundle.js <path-to-bundle.zip>
 */
'use strict';

const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_DIR_SIGNATURE = 0x02014b50;
const LOCAL_FILE_SIGNATURE = 0x04034b50;

function findEndOfCentralDirectory(buf) {
  // EOCD is at least 22 bytes and lives near the end of the file; scan
  // backwards for its signature (handles the common case of no zip comment).
  const minSize = 22;
  for (let i = buf.length - minSize; i >= 0; i--) {
    if (buf.readUInt32LE(i) === EOCD_SIGNATURE) {
      return {
        centralDirCount: buf.readUInt16LE(i + 10),
        centralDirSize: buf.readUInt32LE(i + 12),
        centralDirOffset: buf.readUInt32LE(i + 16),
      };
    }
  }
  throw new Error('Not a valid ZIP file (End Of Central Directory record not found)');
}

function readCentralDirectory(buf, eocd) {
  const entries = [];
  let offset = eocd.centralDirOffset;
  for (let i = 0; i < eocd.centralDirCount; i++) {
    if (buf.readUInt32LE(offset) !== CENTRAL_DIR_SIGNATURE) {
      throw new Error(`Malformed central directory entry at offset ${offset}`);
    }
    const compressionMethod = buf.readUInt16LE(offset + 10);
    const compressedSize = buf.readUInt32LE(offset + 20);
    const uncompressedSize = buf.readUInt32LE(offset + 24);
    const filenameLen = buf.readUInt16LE(offset + 28);
    const extraLen = buf.readUInt16LE(offset + 30);
    const commentLen = buf.readUInt16LE(offset + 32);
    const localHeaderOffset = buf.readUInt32LE(offset + 42);
    const filename = buf.toString('utf8', offset + 46, offset + 46 + filenameLen);

    entries.push({
      filename,
      compressionMethod,
      compressedSize,
      uncompressedSize,
      localHeaderOffset,
    });

    offset += 46 + filenameLen + extraLen + commentLen;
  }
  return entries;
}

function extractEntry(buf, entry) {
  const offset = entry.localHeaderOffset;
  if (buf.readUInt32LE(offset) !== LOCAL_FILE_SIGNATURE) {
    throw new Error(`Malformed local file header for ${entry.filename}`);
  }
  const filenameLen = buf.readUInt16LE(offset + 26);
  const extraLen = buf.readUInt16LE(offset + 28);
  const dataStart = offset + 30 + filenameLen + extraLen;
  const compressed = buf.subarray(dataStart, dataStart + entry.compressedSize);

  if (entry.compressionMethod === 0) {
    return compressed; // STORE (no compression)
  }
  if (entry.compressionMethod === 8) {
    return zlib.inflateRawSync(compressed); // DEFLATE
  }
  throw new Error(`Unsupported compression method ${entry.compressionMethod} for ${entry.filename}`);
}

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function verifyBundle(zipPath) {
  const buf = fs.readFileSync(zipPath);
  const eocd = findEndOfCentralDirectory(buf);
  const entries = readCentralDirectory(buf, eocd);

  const manifestEntry = entries.find((e) => e.filename.endsWith('_MANIFEST.json'));
  if (!manifestEntry) {
    return { ok: false, error: 'No _MANIFEST.json found inside the bundle.' };
  }

  const manifest = JSON.parse(extractEntry(buf, manifestEntry).toString('utf8'));
  const results = [];
  let allOk = true;

  for (const fileRecord of manifest.files) {
    const entry = entries.find((e) => e.filename === fileRecord.filename);
    if (!entry) {
      results.push({ filename: fileRecord.filename, status: 'MISSING_FROM_ZIP', ok: false });
      allOk = false;
      continue;
    }

    let data;
    try {
      data = extractEntry(buf, entry);
    } catch (err) {
      // A corrupted/tampered compressed stream fails to inflate at all --
      // that is itself decisive evidence of tampering, so report it as a
      // clean result rather than letting the exception crash the CLI.
      results.push({
        filename: fileRecord.filename,
        status: 'CORRUPT_OR_TAMPERED',
        error: err.message,
        ok: false,
      });
      allOk = false;
      continue;
    }

    const actualHash = sha256(data);
    const ok = actualHash === fileRecord.sha256;
    if (!ok) allOk = false;
    results.push({
      filename: fileRecord.filename,
      expectedSha256: fileRecord.sha256,
      actualSha256: actualHash,
      status: ok ? 'OK' : 'HASH_MISMATCH',
      ok,
    });
  }

  return {
    ok: allOk,
    caseId: manifest.case_id,
    packagedAt: manifest.packaged_at,
    fileCount: manifest.files.length,
    results,
  };
}

function main() {
  const zipPath = process.argv[2];
  if (!zipPath) {
    console.error('Usage: node verify_bundle.js <path-to-bundle.zip>');
    process.exit(2);
  }
  const report = verifyBundle(zipPath);
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.ok ? 0 : 1);
}

if (require.main === module) {
  main();
}

module.exports = { verifyBundle, sha256, findEndOfCentralDirectory, readCentralDirectory, extractEntry };
