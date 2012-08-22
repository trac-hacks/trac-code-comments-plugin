jQuery(function($) {
	var _ = window.underscore;
	$(document).ajaxError( function(e, xhr, options){
		var errorText = xhr.statusText;
		if (-1 == xhr.responseText.indexOf('<html')) {
			errorText += ': ' + xhr.responseText;
		} else {
			var traceback = $('#traceback pre', xhr.responseText).text();
			if (traceback) {
				errorText += '\n\nSee more in the console log.';
				console.log(traceback);
			}
		}
		alert(errorText);
	});


	window.Comment = Backbone.Model.extend({
	});

	window.CommentsList = Backbone.Collection.extend({
		model: Comment,
		url: CodeComments.comments_rest_url,
		comparator: function(comment) {
			return comment.get('time');
		}
	});

	window.CommentView = Backbone.View.extend({
		tagName: 'li',
		template:  _.template(CodeComments.templates.comment),
		initialize: function() {
			this.model.bind('change', this.render, this);
		},
		render: function() {
			$(this.el).html(this.template(_.extend(this.model.toJSON(), {
				delete_url: CodeComments.delete_url,
				active: this.model.id == CodeComments.active_comment_id,
				can_delete: CodeComments.is_admin
			})));
			return this;
		}
	});

	window.TopCommentsView = Backbone.View.extend({
		id: 'top-comments',

		template:  _.template(CodeComments.templates.top_comments_block),
		events: {
			'click button': 'showAddCommentDialog'
		},

		initialize: function() {
			TopComments.bind('add',   this.addOne, this);
			TopComments.bind('reset', this.addAll, this);
		},

		render: function() {
			$(this.el).html(this.template());
			this.$('button').button();
			TopComments.fetch({data: {path: CodeComments.path, revision: CodeComments.revision, line: 0}});
			return this;
		},

		addOne: function(comment) {
			var view = new CommentView({model: comment});
			this.$("ul.comments").append(view.render().el);
		},
		addAll: function() {
			var view = this;
			TopComments.each(function(comment) {
				view.addOne.call(view, comment);
			});
		},
		showAddCommentDialog: function(e) {
			AddCommentDialog.open(TopComments);
		}

	});

	window.LineCommentsView = Backbone.View.extend({
		id: 'preview',
		initialize: function() {
			LineComments.bind('add',   this.addOne, this);
			LineComments.bind('reset', this.addAll, this);
			this.viewPerLine = {};
		},
		render: function() {
			LineComments.fetch({data: {path: CodeComments.path, revision: CodeComments.revision, line__gt: 0}});
			//TODO: + links
		},
		addOne: function(comment) {
			var line = comment.get('line');
			if (!this.viewPerLine[line]) {
				this.viewPerLine[line] = new CommentsForALineView();
				var $tr = $("th#L"+line).parent();
				$tr.after(this.viewPerLine[line].render().el).addClass('with-comments');
			}
			this.viewPerLine[line].addOne(comment);
		},
		addAll: function() {
			var view = this;
			LineComments.each(function(comment) {
				view.addOne.call(view, comment);
			});
		}
	});

	window.CommentsForALineView = Backbone.View.extend({
		tagName: 'tr',
		className: 'comments',
		template: _.template(CodeComments.templates.comments_for_a_line),
		events: {
			'click button': 'showAddCommentDialog'
		},
		render: function() {
			$(this.el).html(this.template());
			this.$('button').button();
			return this;
		},
		addOne: function(comment) {
			var view = new CommentView({model: comment});
			this.line = comment.get('line');
			this.$("ul.comments").append(view.render().el);
		},
		showAddCommentDialog: function() {
			AddCommentDialog.open(LineComments, this.line);
		}
	});

	window.AddCommentDialogView = Backbone.View.extend({
		id: 'add-comment-dialog',
		template:  _.template(CodeComments.templates.add_comment_dialog),
		events: {
			'click button.add-comment': 'createComment',
			'keyup textarea': 'previewThrottled'
		},
		initialize: function(options) {
			this.$el = $(this.el);
		},
		render: function() {
			this.$el.html(this.template({formatting_help_url: CodeComments.formatting_help_url}))
				.dialog({autoOpen: false, title: 'Add Comment'});
			this.$('button.add-comment').button();
			return this;
		},
		open: function(collection, line) {
			this.line = line;
			this.collection = collection;
			var title = 'Add comment for ' + (this.line? 'line '+this.line + ' of ' : '') + CodeComments.path + '@' + CodeComments.revision;
			this.$el.dialog('open').dialog({title: title});
		},
		close: function() {
			this.$el.dialog('close');
		},
		createComment: function(e) {
			var self = this;
			var text = this.$('textarea').val();
			var line = this.line? this.line : 0;
			if (!text) return;
			var options = {
				success: function() {
					self.$('textarea').val('');
					self.$el.dialog('close');
				}
			};
			this.collection.create({text: text, author: CodeComments.username, path: CodeComments.path, revision: CodeComments.revision, line: line}, options);
		},
		previewThrottled: $.throttle(1500, function(e) { return this.preview(e); }),
		preview: function(e) {
			var view = this;
			$.get(CodeComments.preview_url, {text: this.$('textarea').val()}, function(data) {
				view.$('div.preview').html(data);
				view.$('h3').toggle(data !== '');
			});
		}
	});


	window.LineCommentBubblesView = Backbone.View.extend({
		render: function() {
			this.$('tbody tr').not('.comments').hover(
				function() {
					var $th = $('th', this);
					var line = $('a', $th).attr('href').replace('#L', '');
					$('a', $th).css('display', 'none');
					$th.prepend('<a style="" href="#L'+line+'" class="bubble"><span class="ui-icon ui-icon-comment"></span></a>');
					$('a.bubble').click(function(e) {
							e.preventDefault();
							AddCommentDialog.open(LineComments, line);
						})
						.css({width: $th.width(), height: $th.height(), 'text-align': 'center'})
						.find('span').css('margin-left', ($th.width() - 16) / 2);
				},
				function() {
					var $th = $('th', this);
					$('a.bubble', $th).remove();
					$('a', $th).show();
				}
			);
		}
	});

	window.TopComments = new CommentsList();
	window.LineComments = new CommentsList();
	window.TopCommentsBlock = new TopCommentsView();
	window.LineCommentsBlock = new LineCommentsView();
	window.AddCommentDialog = new AddCommentDialogView();
	window.LineCommentBubbles = new LineCommentBubblesView({el: $('table.code')});

	$(CodeComments.selectorToInsertBefore).before(TopCommentsBlock.render().el);
	LineCommentsBlock.render();
	AddCommentDialog.render();
	LineCommentBubbles.render();
});
