from django.conf import settings

from courseware.courses import get_course_overview_with_access
from courseware.user_state_client import DjangoXBlockUserStateClient
from courseware.courses import get_course_overview_with_access
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from util.views import ensure_valid_course_key
from xmodule.modulestore.django import modulestore

# for customization
from .helpers_utils import get_course_outline_block_tree

USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


@ensure_valid_course_key
def check_if_user_has_answered_this_problem(course_id, student_username, location):
    """Find users who answered this problem at this location.
    Right now this only works for problems because that's all
    StudentModuleHistory records.
    """
    course_key = CourseKey.from_string(course_id)

    try:
        usage_key = UsageKey.from_string(location).map_into_course(course_key)
    except (InvalidKeyError, AssertionError):
        return HttpResponse(escape(_(u'Invalid location.')))

    course = get_course_overview_with_access(request.user, 'load', course_key)
    user_state_client = DjangoXBlockUserStateClient()

    try:
        history_entries = list(user_state_client.get_history(student_username, usage_key))
    except DjangoXBlockUserStateClient.DoesNotExist:
		pass
	else:
		return True
	return False


def check_if_user_has_completed_course(student_username, course_id):
    try:
        user = User.objects.get(username=student_username)
    except User.DoesNotExist:
        raise Exception("User does not exist")

	course_key = CourseKey.from_string(course_id)
    course_overview = get_course_overview_with_access(user, 'load', course_key, check_if_enrolled=True)
    course = modulestore().get_course(course_key)

    course_block_tree = get_course_outline_block_tree(user, course_id)
    if not course_block_tree:
        raise Exception("Course outline missing X_X")

	course_sections = course_block_tree.get('children')
	if course_sections is None:
        raise Exception("Course sections missing X_X")

	for section in course_sections:
		if not section.get('complete'):
			return False

		for subsection in section.get('children', []):
			if not subsection.get('complete'):
				return False

			for vertical in subsection.get('children', []):
				if not vertical.get('complete'):
					return False

	return True