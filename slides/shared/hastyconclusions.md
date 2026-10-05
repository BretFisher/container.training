<!-- verified: 2026-10-05 -->
## Let's draw hasty conclusions

- The bottleneck seems to be `rng`

- *What if* we don't have enough entropy and can't generate enough random numbers?

- We need to scale out the `rng` service on multiple machines!

Note: this is a fiction! We have enough entropy. But we need a pretext to scale out.

(In fact, the code of `rng` uses `/dev/urandom`, which never runs out of entropy...
<br/>
...and is [just as good as `/dev/random`](https://www.slideshare.net/slideshow/filippo-plain-simple-reality-of-entropy/54998144).)
