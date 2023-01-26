## Prerequisites

Need to specify a user and a group.

```
docker run -d -v /data/emy:/app/data \
  -p 3399:3399 -p 3340:3340 \
  addictedcs/soundfingerprinting.emy:latest
```
