Release Instructions
====================

Here's some info on what needs to be done before each release:

- Update the CHANGELOG (add any needed entries and update the version heading)
- Update the version number in ``__about__.py``
- Run `python -m instrumental.parse_modules` from the Instrumental directory to regenerate `driver_info.py`
- Commit and push these changes
- Wait to verify that the builds, tests, and documentation builds all succeed
- Tag the commit with the version number and push the tag
- Set up the release info on GitHub
- Verify that Travis CI and AppVeyor have successfully deployed to PyPI
