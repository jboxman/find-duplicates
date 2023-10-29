const { basename, dirname } = require('path');
const fs = require('fs');
const qs = require('qs');

const dir = require('node-dir');
const exiftool = require('@logion/node-exiftool');
const createCsvWriter = require('csv-writer').createArrayCsvStringifier;

const { api, prepareData, loadExcludeFile } = require('.');

const ep = new exiftool.ExiftoolProcess();

module.exports = async function action(directory, options) {
  if (!fs.existsSync(directory)) {
    process.exitCode = 1;
    return;
  }

  const excludes = options.excludeFrom
    ? await loadExcludeFile(options.excludeFrom)
    : {};
  const excludeArtists = (excludes.artists || []).reduce((accum, pat) => {
    return accum.concat(new RegExp(`^${escapeRe(pat)}`, 'i'));
  }, []);
  const excludeAlbums = (excludes.albums || []).reduce((accum, pat) => {
    return accum.concat(new RegExp(`^${escapeRe(pat)}`, 'i'));
  }, []);

  // In Emy, coverage overrides confidence when both values are equal
  let confidence = false;
  const urlArgs = {};

  if (options.confidence) {
    urlArgs['minConfidence'] = options.confidence;
    confidence = true;
  }
  if (options.coverage) {
    urlArgs['minCoverage'] = options.coverage;
    confidence = true;
  }
  if (!confidence) urlArgs['minConfidence'] = '.90';

  const paths = await dir
    .promiseFiles(directory)
    .then((paths) => paths.filter((path) => /\.mp3$/.test(path)));

  if (paths.length <= 0) return;

  const header = [
    'filename',
    'directory',
    'title',
    'album',
    'artist',
    'success',
    'confidence',
    'coverage',
    'info',
  ];
  const csvWriter = createCsvWriter({
    header,
  });

  await ep.open();

  console.log(csvWriter.getHeaderString().trim());

  for (const path of paths) {
    const localCsvWriter = createCsvWriter({ header, alwaysQuote: true });
    const { formData, fields: metadataFields } = await prepareData({
      ep,
      path,
    });

    let fields = [];
    let response = {};
    let error = '';

    if (excludeArtists.find((v) => v.test(metadataFields.artistName))) continue;
    if (excludeAlbums.find((v) => v.test(metadataFields.albumName))) continue;

    try {
      // https://stackoverflow.com/a/50481928
      response = await api.post(`query?${qs.stringify(urlArgs)}`, formData, {
        headers: formData.getHeaders(),
      });
    } catch (err) {
      response.data = [];

      console.error(`Failed to upload: ${path}`);
      console.error(err.message);
      if (err.response)
        console.error(JSON.stringify(err.response.data, null, 2));

      // If the file is large, a 400 response is returned.
      // But a 400 might occur for other reasons as well, such as file corruption.
      if (/empty file/.test(err.response.data.message)) {
        const { size } = fs.statSync(path);
        console.error(
          `Large files are rejected by Emy. File size: ${size} bytes.`
        );
      }

      error = `${err.response.data.code}:${err.response.data.message}`;
    }

    //console.log(JSON.stringify(response.data, null, 2));

    const results = response.data;

    if (results.length <= 0) {
      let row = [
        basename(path),
        dirname(path),
        metadataFields.songTitle,
        metadataFields.albumName,
        metadataFields.artistName,
      ];
      if (error) row.push('Error');
      if (!error) row.push('No');
      fields.push(row.concat(['', '', error]));
    } else {
      let row = [
        basename(path),
        dirname(path),
        metadataFields.songTitle,
        metadataFields.albumName,
        metadataFields.artistName,
        'Yes',
      ];
      row.push(results[0].audio.coverage.queryCoverage);
      row.push(results[0].audio.coverage.trackCoverage);
      row.push(
        results
          .map((item) => `${item.track.title}:${item.track.artist}`)
          .join(', ')
      );
      fields.push(row);
    }

    // Write single row with correct CSV escaping and quoting
    console.log(localCsvWriter.stringifyRecords(fields).trim());
  }

  await ep.close();
};

// From: https://www.abareplace.com/blog/escape-regexp/
function escapeRe(str) {
  return str.replace(/[[\]*+?{}.()^$|\\-]/g, '\\$&');
}
