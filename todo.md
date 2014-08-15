# Why

Handling comment subscriptions in a single place, rather than trying to work
out who we should and should not notify, will improve both our code and the user
experience.

# How

We will store subscriptions in a new model, and automatically create subscriptions when certain events happen.

# What

We will create a new model for subscriptions, and listeners for comments, attachments and changesets. Then we will refactor the comment notification code to use the subscriptions instead of determining recipients.

# Caveats

No UI will be in this branch.

Need to figure out how to handle blanket subscriptions.

# Tasks

## Subscriptions

- [x] model
 - [x] create
 - [x] update
 - [x] delete
 - [x] query
- [x] db
- [ ] api

## Listeners

- [x] comments_created - create a subscription for the comment author
- [x] attachment_added - create a subscription for the attachment author
- [x] attachment_deleted - remove all subscriptions for the attachment (should we also remove all comments?)
- [x] attachment_reparented - update all subscriptions for the attachment
- [x] changeset_added - create a subscription for the changeset author
- [x] changeset_modified - update the subscription (author?)
