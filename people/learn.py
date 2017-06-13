# coding: utf-8

"""
Module that handle predictive thing about people
@author: Sébastien Renard (sebastien.renard@digitalfox.org)
@license: AGPL v3 or newer (http://www.gnu.org/licenses/agpl-3.0.html)
"""

from background_task import background

HAVE_SCIKIT = True
try:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.neighbors import NearestNeighbors
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, Normalizer
except ImportError:
    HAVE_SCIKIT = False

from django.db.models import Count, Sum, Min, Max
from django.core.cache import cache

from staffing.models import Timesheet
from leads.models import Lead
from people.models import Consultant


CONSULTANT_SIMILARITY_MODEL_CACHE_KEY = "PYDICI_CONSULTANT_SIMILARITY_MODEL"
SIMILARITY_CONSULTANT_IDS_CACHE_KEY = "PYDICI_LEAD_SIMILARITY_CONSULTANTS_IDS"

############# Features extraction ##########################

def consultant_cumulated_experience(consultant):
    features = dict()
    timesheets = Timesheet.objects.filter(consultant=consultant, mission__nature="PROD").order_by("mission__id")
    timesheets = timesheets.values_list("mission__lead__id").annotate(Sum("charge"))

    for lead_id, charge in timesheets:
        for tag in Lead.objects.get(id=lead_id).tags.all():
            features[tag.name] = features.get(tag.name, 0) + charge

    features["profil"] = consultant.profil.level * 100
    #TODO: add experience (missing in model)
    return features


############# Model definition ##########################
def get_similarity_model():
    model = Pipeline([("vect", DictVectorizer()),
                      ("norm", Normalizer()),
                      ("neigh", NearestNeighbors(n_neighbors=6))])
    return model


############# Entry points for prediction ##########################
def predict_similar(consultant):
    model = compute_consultant_similarity.now()
    consultants_ids = cache.get(SIMILARITY_CONSULTANT_IDS_CACHE_KEY)
    similar_consultants = []
    if model is None:
        # cannot compute model (ex. not enough data, no scikit...)
        return []
    features = consultant_cumulated_experience(consultant)
    vect = model.named_steps["vect"]
    neigh = model.named_steps["neigh"]
    norm= model.named_steps["norm"]
    indices = neigh.kneighbors(norm.transform(vect.transform(features)), return_distance=False)
    if indices.any():
        try:
            similar_consultants_ids = [consultants_ids[indice] for indice in indices[0]]
            similar_consultants = Consultant.objects.filter(pk__in=similar_consultants_ids).exclude(pk=consultant.id).select_related()
        except IndexError:
            print("While searching for consultant similarity, some consultant disapeared !")
    return similar_consultants


############# Entry points for computation ##########################

@background
def compute_consultant_similarity():
    """Compute a model to find similar consultants and cache it"""

    if not HAVE_SCIKIT:
        return

    model = cache.get(CONSULTANT_SIMILARITY_MODEL_CACHE_KEY)
    if model is None:
        consultants = Consultant.objects.filter(active=True, productive=True)
        if consultants.count() < 5:
            # Cannot learn anything with so few data
            return
        learn_features = []
        for consultant in consultants:
            learn_features.append(consultant_cumulated_experience(consultant))
        model = get_similarity_model()

        model.fit(learn_features)
        cache.set(CONSULTANT_SIMILARITY_MODEL_CACHE_KEY, model, 3600 * 24 * 7)
        cache.set(SIMILARITY_CONSULTANT_IDS_CACHE_KEY, [i.id for i in consultants], 3600 * 24 * 7)

    return model