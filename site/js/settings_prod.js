Raven.config('https://7354fe0b5b1d46b4ae20aa0f6d0e30ba@sentry.io/1222602').install()

AWS.config.region = 'us-east-1';
AWS.config.credentials = new AWS.CognitoIdentityCredentials({IdentityPoolId: 'us-east-1:48bf35ba-ba12-4319-81d3-8bad0d66faad'});

k8aListSQS = new AWS.SQS({params: {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/022190504632/k8aListQueue'}});
k8aPostSQS = new AWS.SQS({params: {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/022190504632/k8aPostQueue'}});
