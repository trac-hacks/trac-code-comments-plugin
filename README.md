Trac plugin for leaving code comments
=====================================

Problem: when doing a code review leaving comments in context is hard.
Gathering all issues from a code review into tickets is also hard.

This plugin allows you to leave comments on files, changesets, and
attachments.

Then, it allows you to send some of these comments into tickets, including
links to these comments and their description.

Features
--------

* Comments on files – you can comment on every file in the repository.

* Inline comments on files – comment on a specific line. The comments appears
in context, below the line in question.

* Comments on changesets – useful when doing code reviews of incoming commits.

* Comments on attachment pages – useful when reviewing patches.

* Wiki Markup – you can use the standard Trac wiki markup inside your
comments.

* Instant preview – to make sure you get the formatting right.

* Sending comments to tickets – you can select arbitrary number of comments
and create a new ticket out of them. The text of the ticket defaults to links
to the comments and their text, but you can edit these before saving the
ticket.

* Comments/ticket cross-refernce – to remember which comments are already in
tickets and which are not.


License
-------
Copyright (C) 2011-2012, Automattic Inc.

This plugin is distributed under the GPLv2 or later license.