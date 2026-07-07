'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const { verifyBundle, sha256 } = require('../verify_bundle.js');

const FIXTURE = path.join(__dirname, '..', '..', '..', 'docs', 'sample-reports', 'CASE-0001_evidence_bundle.zip');

test('sha256() matches Node crypto.createHash for a known input', () => {
  const crypto = require('node:crypto');
  const input = Buffer.from('hello world');
  const expected = crypto.createHash('sha256').update(input).digest('hex');
  assert.equal(sha256(input), expected);
  assert.equal(sha256(input), 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9');
});

test('verifyBundle() reports ok:true for an untampered bundle produced by evidence_packaging.py', { skip: !fs.existsSync(FIXTURE) }, () => {
  const report = verifyBundle(FIXTURE);
  assert.equal(report.ok, true);
  assert.ok(report.fileCount > 0);
  for (const r of report.results) {
    assert.equal(r.status, 'OK');
  }
});

test('verifyBundle() detects a single-byte tamper', { skip: !fs.existsSync(FIXTURE) }, () => {
  const tmpPath = path.join(os.tmpdir(), `tampered-${Date.now()}.zip`);
  const data = Buffer.from(fs.readFileSync(FIXTURE));
  // flip a byte well past the local file headers, inside compressed file data
  data[300] ^= 0xff;
  fs.writeFileSync(tmpPath, data);

  const report = verifyBundle(tmpPath);
  assert.equal(report.ok, false);
  assert.ok(report.results.some((r) => !r.ok));

  fs.unlinkSync(tmpPath);
});

test('verifyBundle() throws a clear error for a non-ZIP file', () => {
  const tmpPath = path.join(os.tmpdir(), `not-a-zip-${Date.now()}.txt`);
  fs.writeFileSync(tmpPath, 'this is not a zip file');
  assert.throws(() => verifyBundle(tmpPath), /End Of Central Directory/);
  fs.unlinkSync(tmpPath);
});
