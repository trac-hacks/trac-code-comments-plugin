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
			TopComments.fetch({data: {path: CodeComments.path, revision: CodeComments.revision, line: 0, page: CodeComments.page}});
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
			var params = {
				data: {
					revision: CodeComments.revision,
					line__gt: 0,
					page: CodeComments.page
				}
			}

			if ("browser" === CodeComments.page)
				params.data.path = CodeComments.path;

			LineComments.fetch(params);
			//TODO: + links
		},
		addOne: function(comment) {
			var line = comment.get('line');
			if (!this.viewPerLine[line]) {
				// get the parent <tr>
				var $tr = ($("th#L"+line).parent().length > 0) ? $("th#L"+line).parent() : $($('td.l, td.r')[line - 1]).parent();

				this.viewPerLine[line] = new CommentsForALineView();
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
		initialize: function(attrs) {
			this.template = _.template(CodeComments.templates.comments_for_a_line_file);

			if ("changeset" === CodeComments.page)
				this.template = _.template(CodeComments.templates.comments_for_a_line_commit);
		},
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
		open: function( collection, line, file, displayLine ) {
			this.displayLine = displayLine || line;
			this.line = line;
			this.collection = collection;
			this.path = ( '' === CodeComments.path ) ? file : CodeComments.path;
			var title = 'Add comment for ';
			if( '' === this.path || typeof this.path === 'undefined' ) {
				title += ( this.displayLine ? 'line ' + this.displayLine + ' of ' : '' )
				      + 'Changeset ' + CodeComments.revision;
			}
			else {
				title += ( this.displayLine ? 'line ' + this.displayLine + ' of ' : '' )
				      + this.path + '@' + CodeComments.revision;
			}
			this.$el.dialog( 'open' ).dialog( { title: title } );
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
			this.collection.create({text: text, author: CodeComments.username, path: this.path, revision: CodeComments.revision, line: line, page: CodeComments.page}, options);
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
			// changeset view: add toggle spans to THs so we can hide/show their contents
			$( 'table.trac-diff tbody tr th' ).not( '.comments' ).each( function( i, elem ) {
				elem.innerHTML = '<span class="toggle">' + elem.innerHTML + '</span>';
			} );

			var callbackMouseover = function( event ) {
				var $th = ( $( 'th', this ).length ) ? $( 'th', this ) : $( this ),
					line = $( 'a', $th ).attr( 'href' ).replace( '#L', '' ),
					file = $th.parents( 'li' ).find( 'h2>a:first' ).text();

				$( 'a', $th ).css( 'display', 'none' );

				$th.prepend( '<a title="Comment on this line" href="#L' + line + '" class="bubble"><span class="ui-icon ui-icon-comment"></span></a>' );

				$( 'a.bubble' ).click( function( e ) {
					e.preventDefault();
					AddCommentDialog.open( LineComments, line, file );
				} )
				.css( { width: $th.width(), height: $th.height(), 'text-align': 'center' } )
				.find( 'span' ).css( 'margin-left', ( $th.width() - 16 ) / 2 );
			};

			// special mouseovers for the changeset line view
			var changesetCallbackMouseover = function( event ) {
				var $th = ( $( 'th', this ).length) ? $( 'th', this ) : $( this ),
					item = $th[1],
					line = $.inArray( item, $( 'table.trac-diff tbody tr th:odd' ).not( '.comments' ) ) + 1;

				var displayLine = $( item ).text().trim() || $( $th[0] ).text() + ' (deleted)';

				$( 'span.toggle', item ).css( 'display', 'none' );

				$( item ).prepend( '<a title="Comment on this line" href="#L' + line + '" class="bubble"><span class="ui-icon ui-icon-comment"></span></a>' );

				$( 'a.bubble' ).click( function( e ) {
					e.preventDefault();
					AddCommentDialog.open( LineComments, line, '', displayLine );
				})
				.css( { width: $th.width(), height: $th.height(), 'text-align': 'center' } )
				.find( 'span' ).css( 'margin-left', ( $th.width() - 16 ) / 2 );
			};

			var callbackMouseout = function( event ) {
				var $th = $( 'th', this ).length ? $( 'th', this ) : $( this );
				$( 'a.bubble', $th ).remove();
				$( 'a', $th ).css( 'display', '' );
				$( 'span.toggle', $th ).css( 'display', '' );
			};

			this.$( 'table.trac-diff tbody tr' ).not( '.comments' ).hover( changesetCallbackMouseover, callbackMouseout );
			this.$( 'table.code tbody tr' ).not( '.comments' ).hover( callbackMouseover, callbackMouseout );
		}
	});

	window.TopComments = new CommentsList();
	window.LineComments = new CommentsList();
	window.TopCommentsBlock = new TopCommentsView();
	window.LineCommentsBlock = new LineCommentsView();
	window.AddCommentDialog = new AddCommentDialogView();
	window.LineCommentBubbles = new LineCommentBubblesView({el: $('#preview, .diff .entries')});

	$(CodeComments.selectorToInsertBefore).before(TopCommentsBlock.render().el);
	LineCommentsBlock.render();
	AddCommentDialog.render();
	LineCommentBubbles.render();
});
