Trac plugin for leaving code comments
=====================================

Problem: when doing a code review leaving comments in context is hard.
Gathering all issues from a code review into tickets is also hard.

This plugin allows you to leave comments on files, changesets, and
attachments.

Then, it allows you to send some of these comments to tickets, including
links to these comments and their description.

Installation
------------

Pick an `.egg` file from the Downloads section and place it in the `plugins/`
directory of your Trac install.

Trac Code Comments plugin requres at least python 2.4 and runs on Trac 0.12.

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

Contributing
------------

We'd love your help!

If you are a developer, feel free to fork the project here, on github and
submit a pull request with your changes.

If you are a designer and have UI suggestions, [open an issue](https://github.com/Automattic/trac-code-comments-plugin/issues) and we'll make sure to address your concerns.

If you want to help with copy, or just wanna say how great or sucky we are
[creating an issue](https://github.com/Automattic/trac-code-comments-plugin/issues) is the way to go.

You can find help with setting up a local development environment in the [`HACKING`](https://github.com/Automattic/trac-code-comments-plugin/blob/master/HACKING) file in this repostitory,

Roadmap
-------

Nobody can predict the future, but here are some features on the roadmap:
* Line-level comments for changesets and diff atatchments, too
* E-mail notifictaions

License
-------
Copyright (C) 2011-2012, Automattic Inc.

This plugin is distributed under the GPLv2 or later license.