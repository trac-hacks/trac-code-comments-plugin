jQuery(function($) {
	var console = window.console || {log: function() {}};

	var page_name = CodeComments.page;
	var args = CodeComments.args;
	var pages = {};

	var dispatch = function() {
		if (pages[page_name]) {
			var page = new pages[page_name](args);
			page.init();
		} else {
			console.log("Unknown page: "+page_name);
		}		
	}

	pages['browser'] = function(args) {
		
		this.init = function() {
			getComments(args.path, args.revision, 0, this.loadTopComments);
			getComments(args.path, args.revision, null, this.loadLineComments);
		}
		
		this.loadTopComments = function(comments) {
			console.log(comments);
		}
		
		this.loadLineComments = function(comments) {
			
		}
	}	
	
	var getComments = function(path, revision, line, callback) {
		callback([{id: 5, html: "Wonka <code>wonka</code>", text: "Wonka {{{wonka}}}", path: '', revision: 2, line: 0, author: 'nb', time: 1321879157}]);
	}
	
	dispatch();
});
