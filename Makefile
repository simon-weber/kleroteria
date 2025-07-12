init:
	pip install -r dev-requirements.txt && \
	cd site && \
	bundle install && \
	echo "also, manually install a jdk and https://github.com/netlify/netlifyctl"

localstack:
	LOCALSTACK_SERVICES=ses,lambda,sqs,dynamodb localstack start --docker --detached --no-banner && \
	localstack wait && \
	cd site && \
	bundle exec jekyll serve --host=0.0.0.0

fixtures:
	python -c 'from kleroteria.test.aws_fixtures import main; main()'

invoke_list:
	cd lambdas/list_ingest/ && \
	lambda invoke

invoke_post:
	cd lambdas/post_ingest/ && \
	lambda invoke

invoke_lottery:
	cd lambdas/post_ingest/ && \
	bash -c 'lambda invoke --event-file=<(echo -n "{\"action\": \"pick_winner\", \"secret\": \"dummy_secret\"}")'

deploy-all:
	cd site && \
	rm -rf _netlify && \
	JEKYLL_ENV=production bundle exec jekyll build -d _netlify && \
	cd .. && \
	netlifyctl deploy -b site/_netlify && \
	cd lambdas/list_ingest/ && \
	lambda deploy --config-file config_prod.yaml --requirements ../../lambda-requirements.txt && \
	cd ../post_ingest/ && \
	lambda deploy --config-file config_prod.yaml --requirements ../../lambda-requirements.txt && \
	cd ../manual_email/ && \
	lambda deploy --config-file config_prod.yaml --requirements ../../lambda-requirements.txt

deploy-site:
	cd site && \
	rm -rf _netlify && \
	JEKYLL_ENV=production bundle exec jekyll build -d _netlify && \
	cd .. && \
	netlifyctl deploy -b site/_netlify

clean:
	rm -rf /tmp/aws-lambda* && \
	rm -rf lambdas/*/dist/*

test:
	pytest -vs kleroteria/test

pip-compile:
	# python-lambda can't handle inline comments
	pip-compile -r --no-annotate --output-file all-requirements.txt all-requirements.in setup.py && \
	pip-compile -r -c all-requirements.txt --no-annotate --output-file requirements.txt setup.py && \
	pip-compile -r -c all-requirements.txt dev-requirements.in && \
	pip-compile -r -c all-requirements.txt lambda-requirements.in && \
	pip-sync dev-requirements.txt

viewdead:
	aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/022190504632/k8aListDeadLetter
