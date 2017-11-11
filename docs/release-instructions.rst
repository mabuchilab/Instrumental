Release Instructions
====================

Here's some info on what needs to be done before each release:

- Update the CHANGELOG (add any needed entries and update the version heading)
- Update the version number in ``__about__.py``
- Update the version number in ``instrumental.conf.default``
- Commit and push these changes
- Wait to verify that the builds, tests, and documentation builds all succeed
- Tag the commit with the version number and push the tag
- Set up the release info on GitHub
- Download a copy of the GitHub source and build the distributions
- Upload these dists using ``twine``
