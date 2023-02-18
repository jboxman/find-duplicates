//const path = require('path');
const fs = require('fs');
const dir = require('node-dir');
const exiftool = require('@logion/node-exiftool');

const { api, prepareData } = require('.');

const ep = new exiftool.ExiftoolProcess();

module.exports = async function action(directory, options, cmd) {
  if (!fs.existsSync(directory)) {
    process.exitCode = 1;
    return;
  }

  const paths = await dir
    .promiseFiles(directory)
    .then((paths) => paths.filter((path) => /\.mp3$/.test(path)));

  if (paths.length <= 0) return;

  await ep.open();

  for (const path of paths) {
    const formData = prepareData({ ep, path });
    let response = {};
    try {
      // https://stackoverflow.com/a/50481928
      response = await api.post('tracks', formData, {
        headers: formData.getHeaders(),
      });
      console.error(`Uploaded: ${path}`);
    } catch (err) {
      response.data = [];

      console.error(`Failed to upload: ${path}`);
      console.error(err.message);
      if (err.response)
        console.error(JSON.stringify(err.response.data, null, 2));
      if (/empty file/.test(err.response.data.message)) {
        const { size } = fs.statSync(path);
        console.log(
          `Large files are rejected by Emy. File size: ${size} bytes.`
        );
      }
    }
  }

  await ep.close();
};
