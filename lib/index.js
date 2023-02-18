const { default: axios } = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const fsPromises = require('fs').promises;
const { existsSync } = require('fs');
const { createId } = require('@paralleldrive/cuid2');
const yaml = require('js-yaml');

const api = axios.create({
  baseURL: 'http://localhost:3340/api/v1.1/',
  // Admin
  headers: { authorization: 'Basic QWRtaW46' },
});

const pickTag = (tagGroup) => (allTags) => {
  const raw =
    allTags[tagGroup.reverse().find((tag) => allTags.hasOwnProperty(tag))];
  if (!['string', 'number'].includes(typeof raw)) return '';
  return String(raw).trim();
};

// https://exiftool.org/TagNames/ID3.html
const pickTitleTag = pickTag([
  'ID3v1:Title',
  'Lyrics3:ExtendedTrackTitle',
  'ID3v2_3:Title',
  'ID3v2_4:Title',
]);
const pickAlbumTag = pickTag([
  'ID3v1:Album',
  'Lyrics3:ExtendedAlbumName',
  'ID3v2_3:Album',
  'ID3v2_4:Album',
]);
const pickArtistTag = pickTag([
  'ID3v1:Artist',
  'Lyrics3:ExtendedArtistName',
  'ID3v2_3:Artist',
  'ID3v2_4:Artist',
]);

async function prepareData({ ep, path }) {
  const { data } = await ep.readMetadata(path, ['G1']);

  const fields = {};

  if (pickAlbumTag(data[0])) fields['albumName'] = pickAlbumTag(data[0]);
  if (pickTitleTag(data[0])) fields['songTitle'] = pickTitleTag(data[0]);
  if (pickArtistTag(data[0])) fields['artistName'] = pickArtistTag(data[0]);

  const payload = {
    id: createId(),
    mediaType: 'Audio',
  };

  // Avoids: Error value cannot be null (Parameter 'value') could not be handled gracefully
  if (data[0]['System:FileName'])
    payload['metaFields[filename]'] = data[0]['System:FileName'];
  if (fields['albumName']) payload['metaFields[album]'] = fields['albumName'];
  if (fields['songTitle']) payload['title'] = fields['songTitle'];
  if (fields['artistName']) payload['artist'] = fields['artistName'];

  const formData = new FormData();

  for (const [key, value] of Object.entries(payload)) {
    formData.append(key, value);
  }

  formData.append('file', fs.createReadStream(path));

  // Missing Content-length header
  // 'Content-Length': https://stackoverflow.com/a/70982610
  //console.log(formData.getHeaders());

  return {
    formData,
    fields,
  };
}

async function loadExcludeFile(file = '') {
  if (!file) {
    console.error(`No configuration found, skipping.`);
    return {};
  }

  if (!existsSync(file)) {
    console.error(`Cannot open configuration file: ${file}`);
    throw new Error();
  }

  try {
    return yaml.load(await fsPromises.readFile(file, { encoding: 'utf8' }));
  } catch (e) {
    if (e instanceof Error && e.name == 'YAMLException') {
      console.error(`Cannot parse configuration file. The YAML is invalid.`);
      throw e;
    }
    throw e;
  }
}

module.exports = {
  api,
  prepareData,
  loadExcludeFile,
};
