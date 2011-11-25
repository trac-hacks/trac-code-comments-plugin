jQuery(function($) {
	_.extend(Backbone.Collection.prototype, {
		createAndFetch : function(model, options) {
			var coll = this;
			options || (options = {});
			model = this._prepareModel(model, options);
			if (!model) return false;
			var success = options.success;
			options.success = function(nextModel, resp, xhr) {
				nextModel = coll._prepareModel(nextModel, options);
				nextModel.fetch();
				console.log(nextModel);
				coll.add(nextModel, options);
				if (success) success(nextModel, resp, xhr);
			};
			model.save(null, options);
			return model;
		}
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
			var text = this.$('textarea').val();
			if (!text) return;
			TopComments.createAndFetch({text: text, author: 'nb', path: CodeComments.path, revision: CodeComments.revision, line: 0});
		},
	});


	window.TopCommentsBlock = new TopCommentsView();
	window.AddCommentDialog = new AddCommentDialogView;

	$(CodeComments.selectorToInsertBefore).before(TopCommentsBlock.render().el);
	AddCommentDialog.render();
});