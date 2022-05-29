Release Instructions
====================

Here's some info on what needs to be done before each release:

- Update the CHANGELOG (add any needed entries and update the version heading)
- Update the version number in ``__about__.py``
- Run ``python -m instrumental.parse_modules`` from the Instrumental directory to regenerate ``driver_info.py``
- [Locally build and review the documentation]
- Verify the PyPI description (generated from ``README.rst``) is valid:

  - ``python setup.py sdist``
  - ``twine check dist/*``

- Commit and push these changes
- Wait to verify that the builds, tests, and documentation builds all succeed
- Tag the commit with the version number and push the tag

  - ``git tag -m "Release 0.x" 0.x``
  - ``git push --tags``

- Set up the release info on GitHub

  - Go to releases, "Draft a new release"
  - Choose the newly pushed tag
  - Copy in the CHANGELOG section for this release, convert headings to use ``###``
  - Check "This is a pre-release"
  - Click "Publish release" (DO NOT save as a draft. This will mess up the Github Actions you'll never publish to TestPyPI)
  - Wait for PyPI GitHub action to run, verify upload succeeded
  - Uncheck "This is a pre-release" and re-publish
  - Verify that the PyPI GitHub action has deployed to the real PyPI
