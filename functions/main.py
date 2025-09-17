# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions.options import set_global_options
from firebase_admin import initialize_app

from constants.constants import MAX_INSTANCES

# Import routes
from routes.landing_site_contact_form_lead import store_landing_site_contact_form_lead, get_landing_site_contact_form_lead
from routes.merchant import store_merchant, get_merchants, store_pending_merchant, get_pending_merchants, approve_pending_merchant, deny_pending_merchant
from routes.openai import generate_social_media_post, generate_chinese_social_media_post

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=MAX_INSTANCES)

# Initialize Firebase Admin SDK
initialize_app()

