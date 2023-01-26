## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```

## References

- [Audio Fingerprinting API](https://emysound.com/blog/open-source/2021/06/05/audio-fingerprinting-api.html): 
- [JSON API](https://emysound.readme.io/reference/json-api)
