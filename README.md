# Kleroteria

An email lottery and spiritual successor to [The Listserve](https://thelistservearchive.com/).
You can join at [kleroteria.org](https://www.kleroteria.org/).

For more information about how it works, see [Running Kleroteria for free by (ab)using free tiers](https://simon.codes/2018/07/09/running-kleroteria-for-free-by-abusing-free-tiers.html).

## setup
* create + activate a python3 virtualenv
* `make init`

## dev
* serve locally: `make localstack` then in another shell `make fixtures`. The site runs at localhost:4000. Use `make invoke_*` to run the various lambdas.
* run tests: `make test`
