jQuery(function($) {
	window.Comment = Backbone.Model.extend({
	});

	window.CommentsList = Backbone.Collection.extend({
		model: Comment,
		url: '/code-comments/comments',
		comparator: function(comment) {
			return comment.get('time');
		}
	});
	window.TopComments = new CommentsList;

	window.TopCommentView = Backbone.View.extend({
		tagName: 'li',
		template:  _.template(CodeComments.templates.top_comment),
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
		id: 'top-comments',

		template:  _.template(CodeComments.templates.top_comments_block),
		events: {
			'click #add-comment': 'showAddCommentDialog'
		},

		initialize: function() {
			this.textarea = this.$('#comment-text');
			TopComments.bind('add',	  this.addOne, this);
			TopComments.bind('reset', this.addAll, this);
		},

		render: function() {
			$(this.el).html(this.template());
			this.$('#add-comment').button();
			TopComments.fetch({data: {path: CodeComments.path, revision: CodeComments.revision, line: 0}});
			return this;
		},

		addOne: function(comment) {
			var view = new TopCommentView({model: comment});
			this.$("ul").append(view.render().el);
		},
		addAll: function() {
			var view = this;
			TopComments.each(function(comment) {
				view.addOne.call(view, comment);
			});
		},
		showAddCommentDialog: function(e) {
			AddCommentDialog.open();
		}

	});

	window.AddCommentDialogView = Backbone.View.extend({
		template:  _.template(CodeComments.templates.add_comment_dialog),
		events: {
			'click .add-comment': 'createComment'
		},
		initialize: function() {
			this.$el = $(this.el);
		},
		render: function() {
			this.$el.html(this.template()).dialog({autoOpen: false, title: 'Add Comment'});
			return this;
		},
		open: function() {
			this.$el.dialog('open');
		},
		close: function() {
			this.$el.dialog('close');
		},
		createComment: function(e) {
			alert('Not Implemented');
		},
	});


	window.TopCommentsBlock = new TopCommentsView();
	window.AddCommentDialog = new AddCommentDialogView;

	$(CodeComments.selectorToInsertBefore).before(TopCommentsBlock.render().el);
	AddCommentDialog.render();
});