# To Install:

1. Install with `pip install -e .` within this folder within the edx platform virtual environment.
2. Add "sparta_pages" to the "ADDL_INSTALLED_APPS" array in `lms.env.json` (you may have to create it if it doesn't exist.)
3. Run migrations.
4. Start/restart the LMS.


## Templates Directory
Add this to envs.common:

TEMPLATES_DIR = {
  ...
  OPENEDX_ROOT / 'features' / 'sparta-pages' / 'sparta_pages' / 'templates',
}

## ADD TO LMS URLS
urlpatterns += [
    url(r'', include('sparta_pages.urls')),
]
