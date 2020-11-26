// parse the querystring.
// https://stackoverflow.com/a/2880929/1231454
var urlParams;
(window.onpopstate = function () {
  var match,
  pl     = /\+/g,
    search = /([^&=]+)=?([^&]*)/g,
      decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
        query  = window.location.search.substring(1);

        urlParams = {};
        while (match = search.exec(query))
          urlParams[decode(match[1])] = decode(match[2]);
})();

function isValidPost(post){
  // remember that there's linked copy in submit.html explaining this
  return post.length < 3000;
}

function submitPost(){
  gtag('event', 'submit', {
    'event_category': 'mainList',
  });

  document.getElementById('invalid-post').style.display = 'none';
  document.getElementById('post-form').style.display = 'none';
  document.getElementById('spinner').style.display = '';
  document.getElementById('post-success').style.display = 'none';

  const postContents = document.getElementById('postInput').value;
  const subjectContents = document.getElementById('subjectInput').value;

  if (!isValidPost(postContents) || !subjectContents) {
    document.getElementById('invalid-post').style.display = '';
    document.getElementById('post-form').style.display = '';
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('post-success').style.display = 'none';
    return;
  }

  k8aPostSQS.sendMessage({MessageBody: JSON.stringify(['submit', urlParams.id, urlParams.n, postContents, subjectContents])}, function (err, data) {
    var postFormRelateds = document.getElementsByClassName('post-form-related');
    for (var i = 0; i < postFormRelateds.length; i++) {
      postFormRelateds.item(i).style.display = 'none';
    }
    document.getElementById('invalid-post').style.display = 'none';
    document.getElementById('post-form').style.display = 'none';
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('post-success').style.display = '';
    // TODO handle this error
    console.log(err, data);
  });
}

document.addEventListener("DOMContentLoaded", function() {
	document.getElementById('postInput').onkeyup = function () {
		document.getElementById('charCount').innerHTML = 3000 - this.value.length;
	};
});
