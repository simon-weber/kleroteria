AWS.config.region = 'us-east-1';
AWS.config.credentials = new AWS.Credentials('fake_key', 'fake_secret');

k8aListSQS = new AWS.SQS({endpoint: 'http://127.0.0.1:4576', params: {QueueUrl: 'http://localhost:4576/queue/k8aListQueue'}});
k8aPostSQS = new AWS.SQS({endpoint: 'http://127.0.0.1:4576', params: {QueueUrl: 'http://localhost:4576/queue/k8aPostQueue'}});
