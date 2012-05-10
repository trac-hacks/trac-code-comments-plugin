jQuery(document).ready(function($){

	$check_all_checkbox = $('#check-all input');
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