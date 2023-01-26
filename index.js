//const path = require('path');
const { default: axios } = require('axios');
const dir = require('node-dir');
const exiftool = require('@logion/node-exiftool');
const FormData = require('form-data');
const fs = require('fs');
const { createId } = require('@paralleldrive/cuid2');

const api = axios.create({
  baseURL: 'http://localhost:3340/api/v1.1/',
  // Admin
  headers: {'authorization': 'Basic QWRtaW46'}
});
const ep = new exiftool.ExiftoolProcess();

const pickTag = tagGroup => allTags => {
  const raw = allTags[tagGroup.reverse().find(tag => allTags.hasOwnProperty(tag))];
  if(!['string', 'number'].includes(typeof raw)) return '';
  return String(raw).trim();
}

// https://exiftool.org/TagNames/ID3.html
const pickTitleTag = pickTag(['ID3v1:Title', 'Lyrics3:ExtendedTrackTitle', 'ID3v2_3:Title', 'ID3v2_4:Title']);
const pickAlbumTag = pickTag(['ID3v1:Album', 'Lyrics3:ExtendedAlbumName', 'ID3v2_3:Album', 'ID3v2_4:Album']);
const pickArtistTag = pickTag(['ID3v1:Artist', 'Lyrics3:ExtendedArtistName', 'ID3v2_3:Artist', 'ID3v2_4:Artist']);

async function main() {
  const paths = await dir.promiseFiles('./mp3')
    .then(paths => paths.filter(path => /\.mp3$/.test(path)));

    if(paths.length <= 0) return;

    await ep.open();

    for(const path of paths) {
      const { data } = await ep.readMetadata(path, ['G1']);

      const payload = {
        'id': createId(),
        'metaFields[filename]': data[0]['System:FileName'],
        'mediaType': 'Audio'
      }
      // Avoids: Error value cannot be null (Parameter 'value') could not be handled gracefully
      if(pickAlbumTag(data[0])) payload['metaFields[album]'] = pickAlbumTag(data[0]);
      if(pickTitleTag(data[0])) payload['title'] = pickTitleTag(data[0]);
      if(pickArtistTag(data[0])) payload['artist'] = pickArtistTag(data[0]);

      const formData = new FormData();

      for(const [ key, value ] of Object.entries(payload)) {
        formData.append(key, value);
      }

      formData.append('file', fs.createReadStream(path));

      // Missing Content-length header
      //console.log(formData.getHeaders());

      let response;
      try {
        // https://stackoverflow.com/a/50481928
        response = await api.post('tracks', formData, { headers: formData.getHeaders() });
        console.log(`Uploaded: ${path}`);
      }
      catch(err) {
        console.error(`Failed to upload: ${path}`);
        console.error(err.message);
        if(err.response) console.error(JSON.stringify(err.response.data, null, 2));
        if(/empty file/.test(err.response.data.message)) {
          const { size } = fs.statSync(path);
          console.log(`Large files are rejected by Emy. File size: ${size} bytes.`);
        }
      }

    }

    await ep.close();
}

main();
