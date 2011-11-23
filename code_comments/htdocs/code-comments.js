jQuery(function($) {
	window.Comment = Backbone.Model.extend({
	});

	window.Comment = Backbone.Model.extend({
	});

	window.CommentsList = Backbone.Collection.extend({
		model: Comment,
		comparator: function(comment) {
			return comment.get('time');
		}
	});
	window.TopComments = new CommentsList;

	window.TopCommentView = Backbone.View.extend({
		tagName: 'li',
		template:  _.template($('#comment-template').html()),
		events: {
		   'click .delete': 'del',
		},
		initialize: function() {
		   this.model.bind('change', this.render, this);
		   this.model.bind('destroy', this.remove, this);
		},
		render: function() {
		   $(this.el).html(this.template(this.model.toJSON()));
		   return this;
		},
		remove: function() {
		   $(this.el).remove();
		 },
		 del: function() {
			this.model.destroy();
		 }
	});

	window.TopCommentsView = Backbone.View.extend({


		events: {
			'click #add-comment': 'createOnAddButton'
		},

		initialize: function() {
			this.textarea = this.$('#comment-text');
			TopComments.bind('add',	  this.addOne, this);
			TopComments.bind('reset', this.addAll, this);
			TopComments.fetch();
		},

		addOne: function(comment) {
			var view = new TopCommentView({model: comment});
			this.$("ul").append(view.render().el);
		},
		addAll: function() {
			TopComments.each(this.addOne);
		},
		createOnAddButton: function(e) {
			var text = this.textarea.val();
			var author = 'nb';
			if (!text) return;
			TopComments.create({text: text, html: text, author: 'nb', permalink: 'http://dir.bg/',formatted_date: 'Nov 23rd, 2011', time: 5});
		}
	});

	window.TopCommentsBlock = new TopCommentsView;
});