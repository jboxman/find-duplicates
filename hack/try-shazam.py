import sys
#import json
from ShazamAPI import Shazam

path = sys.argv[1]
mp3_file_content_to_recognize = open(path, 'rb').read()

# An argument error is raised if lang and tz are passed in,
# so I edited the ShazamAPI module itself. YMMV

shazam = Shazam(
  mp3_file_content_to_recognize
)

# Return as CSV: filename, track.title, track.subtitle
recognize_generator = shazam.recognizeSong()
# This iterates across the entire file, making possibly dozens of API calls
for offset, result in recognize_generator:
  if len(result['matches']) > 0:

    title = result['track']['title']
    subtitle = result['track']['subtitle']
    url = ''

    if result['track']['share'] and result['track']['share']['href']:
      url = result['track']['share']['href']

    print(f'"{path}","{title}","{subtitle}","{url}"')
    # Usually, if the first attempt isn't accurate, none of them are
    break

    #print(json.dumps(result))
