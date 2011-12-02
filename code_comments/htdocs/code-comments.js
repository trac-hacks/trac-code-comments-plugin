jQuery(function($) {
	$(document).ajaxError( function(e, xhr, options){
		var errorText = xhr.statusText;
		if (-1 == xhr.responseText.indexOf('<html')) {
			errorText += ': ' + xhr.responseText;
		}
		alert(errorText);
	});


	window.Comment = Backbone.Model.extend({
	});

	window.CommentsList = Backbone.Collection.extend({
		model: Comment,
		url: '/code-comments/comments',
		comparator: function(comment) {
			return comment.get('time');
		}
	});

	window.CommentView = Backbone.View.extend({
		events: {
		   'click .delete': 'del',
		},
		initialize: function() {
		   this.model.bind('change', this.render, this);
		   this.model.bind('destroy', this.remove, this);
		},
		render: function() {
		   $(this.el).html(this.template(_.extend(this.model.toJSON(), {
				delete_url: CodeComments.delete_url,
				active: this.model.id == CodeComments.active_comment_id,
				can_delete: CodeComments.is_admin,
			})));
		   return this;
		},
		remove: function() {
		   $(this.el).remove();
		 },
		 del: function() {
			this.model.destroy();
		 }
	});

	window.TopCommentView = CommentView.extend({
		tagName: 'li',
		template:  _.template(CodeComments.templates.top_comment),
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
			this.$("ul.comments").append(view.render().el);
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

	window.LineCommentView = CommentView.extend({
		tagName: 'tr',
		className: 'line-comment',
		template:  _.template(CodeComments.templates.line_comment),
		render: function() {
			$(this.el).attr('data-line', this.model.get('line'));
			return CommentView.prototype.render.call(this);
		}
	});


	window.LineCommentsView = Backbone.View.extend({
		id: 'preview',
		initialize: function() {
			this.textarea = this.$('#comment-text');
			LineComments.bind('add',	  this.addOne, this);
			LineComments.bind('reset', this.addAll, this);
		},
		render: function() {
			LineComments.fetch({data: {path: CodeComments.path, revision: CodeComments.revision, line__gt: 0}});
			//TODO: + links
		},
		addOne: function(comment) {
			var view = new TopCommentView({model: comment});
			var rendered = view.render().el;
			var $line_tr = $("#L"+comment.get('line')).parent();
			var $line_comment_tr = $line_tr.siblings('tr[data-line="'+comment.get('line')+'"]');
			if (!$line_comment_tr.length) {
				$line_tr.after('<tr data-line="'+comment.get('line')+'"><td>&nbsp;</td><td><ul class="comments"></ul></td></tr>');
				$line_comment_tr = $line_tr.siblings('tr[data-line="'+comment.get('line')+'"]');
			}
			$('ul.comments', $line_comment_tr).append(rendered);
		},
		addAll: function() {
			var view = this;
			LineComments.each(function(comment) {
				view.addOne.call(view, comment);
			});
		},
	});

	window.AddCommentDialogView = Backbone.View.extend({
		id: 'add-comment-dialog',
		template:  _.template(CodeComments.templates.add_comment_dialog),
		events: {
			'click .add-comment': 'createComment'
		},
		initialize: function() {
			this.$el = $(this.el);
		},
		render: function() {
			this.$el.html(this.template({formatting_help_url: CodeComments.formatting_help_url}))
				.dialog({autoOpen: false, title: 'Add Comment'});
			this.$('.add-comment').button();
			return this;
		},
		open: function() {
			this.$el.dialog('open');
		},
		close: function() {
			this.$el.dialog('close');
		},
		createComment: function(e) {
			var self = this;
			var text = this.$('textarea').val();
			if (!text) return;
			var options = {
				success: function() {
					self.$('textarea').val('');
					self.$el.dialog('close');
				}
			}
			TopComments.create({text: text, author: CodeComments.username, path: CodeComments.path, revision: CodeComments.revision, line: 0}, options);
		},
	});

	window.TopComments = new CommentsList;
	window.LineComments = new CommentsList;
	window.TopCommentsBlock = new TopCommentsView;
	window.LineCommentsBlock = new LineCommentsView;
	window.AddCommentDialog = new AddCommentDialogView;

	$(CodeComments.selectorToInsertBefore).before(TopCommentsBlock.render().el);
	LineCommentsBlock.render();
	AddCommentDialog.render();
});