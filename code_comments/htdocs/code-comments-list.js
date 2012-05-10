jQuery(document).ready(function($){

	$('#send-to-ticket').click(function(e) {
		e.preventDefault();
		var ids = $('table.code-comments td.check input:checked' ).map(function(i, e) {return e.id.replace('checked-', '')}).get();
		if (!ids.length) {
			alert("Please select comments to include in the ticket.");
			return;
		}
		window.location = $(this).data('url') + '?ids=' + ids.join(',');
	});

	$check_all_checkbox = $('th.check input');
	$all_checkboxes = $('td.check input')

	$check_all_checkbox.click(function(){
		$this = $(this);
		var checked = $this.attr('checked');
		$all_checkboxes.attr('checked', checked);
	});

	$all_checkboxes.click(function(){
		var $this = $(this);
		var all_checked = true;

		if ( !$this.attr('checked') ) {
			all_checked = false;
		} else {
			$all_checkboxes.each(function(){
				if ( !$(this).attr('checked') ) {
					all_checked = false;
				}
			});
		}

		$check_all_checkbox.attr('checked', all_checked);

	});

});