NOT ACTIVELY MAINTAINED
=======================

This Trac plugin served an important purpose for us, but it was replaced with Phabricator or GitHub in many Automattic properties.


Code Comments, an enhancement for Trac
=====================================

The problem is two-fold. When reviewing code, it's difficult to
associate your comments with their appropriate context. Then,
collecting all of these new issues into actionable tickets requires
a lot of manual effort.

This plugin allows you to leave comments on top of files, changesets, and
attachments. Once you've added all of your comments, you can send them to
tickets. These include links to these comments and their description.

It's GitHub, in your Trac.

Installation
------------

Pick an `.egg` file from the Downloads section and place it in the `plugins/`
directory of your Trac install.

Alternatively build your own egg by checking out the repository and running
`python setup.py bdist_egg` in your working copy. Copy the resultant .egg to
your `plugins` directory.

Trac Code Comments plugin requres at least python 2.4 and runs on Trac 0.12.

Enable all the modules through the admin web UI or by editing `trac.ini`.


Upgrading
---------

Install the latest version of the plugin (as above).

Run `trac-admin <path-to-environment> upgrade` to update the database.

Enable any new modules through the admin web UI or by editing `trac.ini`.

Run `trac-admin <path-to-environment> subscription seed` to create
subsriptionfor existing attachments, changesets and comments.


Features
--------

* Comments on files – you can comment on every file in the repository.

* Inline comments on files – comment on a specific line. The comments appears
in context, below the line in question.

* Comments on changesets – useful when doing code reviews of incoming commits.

* Inline comments on changesets - comment on a specific line of the changeset.

* Comments on attachment pages – useful when reviewing patches.

* Wiki Markup – you can use the standard Trac wiki markup inside your
comments.

* Instant preview – to make sure you get the formatting right.

* Sending comments to tickets – you can select arbitrary number of comments
and create a new ticket out of them. The text of the ticket defaults to links
to the comments and their text, but you can edit these before saving the
ticket.

* Comments/ticket cross-reference – to remember which comments are already in
tickets and which are not.

* Notifications – if you have configured Trac to email ticket notifications
then comment notifications will just work!

 * Subscriptions – Authors of changesets and attachments, and anyone who
creates a comment are subscribed to notifications of comments; to have changeset authors automatically subscribed, your repositories must be configured for [synchronisation](http://trac.edgewall.org/wiki/TracRepositoryAdmin#Synchronization) with Trac

Screenshots
-----------

![Inline comment screenshot](https://github.com/Automattic/trac-code-comments-plugin/raw/master/screenshots/0.png)

Contributing
------------

We'd love your help!

If you are a developer, feel free to fork the project here on GitHub, and
submit a pull request with your changes.

If you are a designer and have UI suggestions, [open an issue](https://github.com/Automattic/trac-code-comments-plugin/issues), and we'll make sure to address your concerns.

If you want to help with copy, or just wanna say how great or awful we are,
[creating an issue](https://github.com/Automattic/trac-code-comments-plugin/issues) is the way to go.

You can find help with setting up a local development environment in the [`HACKING`](https://github.com/Automattic/trac-code-comments-plugin/blob/master/HACKING) file in this repository.

Roadmap
-------

Nobody can predict the future, but here are some features on the roadmap:

* Line-level comments for diff attachments, too
* E-mail notifications

License
-------
Copyright (C) 2011-2012, Automattic Inc.

This plugin is distributed under the GPLv2 or later license.
