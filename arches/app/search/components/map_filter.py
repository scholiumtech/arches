import logging
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from django.utils.translation import gettext as _
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search.elasticsearch_dsl_builder import (
    Bool,
    Match,
    Query,
    Nested,
    Term,
    Terms,
    GeoShape,
)
from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.mappings import RESOURCES_INDEX

logger = logging.getLogger(__name__)

details = {
    "searchcomponentid": "",
    "name": "Map Filter",
    "icon": "fa fa-map-marker",
    "modulename": "map_filter.py",
    "classname": "MapFilter",
    "type": "map-filter-type",
    "componentpath": "views/components/search/map-filter",
    "componentname": "map-filter",
    "config": {},
}


class MapFilter(BaseSearchFilter):
    def append_dsl(self, search_query_object, **kwargs):
        permitted_nodegroups = kwargs.get("permitted_nodegroups")
        include_provisional = kwargs.get("include_provisional")
        search_query = Bool()
        querysting_params = self.request.GET.get(self.componentname, "")
        spatial_filter = JSONDeserializer().deserialize(querysting_params)
        if details["componentname"] not in search_query_object:
            search_query_object[details["componentname"]] = {}

        if "features" in spatial_filter:
            if len(spatial_filter["features"]) > 0:
                feature_geom = spatial_filter["features"][0]["geometry"]
                feature_properties = {}
                if "properties" in spatial_filter["features"][0]:
                    feature_properties = spatial_filter["features"][0]["properties"]

                add_geoshape_query_to_search_query(
                    feature_geom,
                    feature_properties,
                    permitted_nodegroups,
                    include_provisional,
                    search_query,
                )
                search_query_object["query"].add_query(search_query)

        elif "featureid" in spatial_filter and "resourceid" in spatial_filter:
            se = SearchEngineFactory().create()
            main_query = Query(se)
            nested_query = Nested(path="geometries")
            match_feature = Match(
                field="geometries.geom.features.id", query=spatial_filter["featureid"]
            )

            # Create a Bool query for conditions inside the nested path
            bool_nested_query = Bool()
            bool_nested_query.must(match_feature.dsl)
            nested_query.add_query(bool_nested_query.dsl)

            bool_query = Bool()
            match_resource = Term(
                field="resourceinstanceid", term=spatial_filter["resourceid"]
            )
            bool_query.must(
                match_resource.dsl
            )  # Match resource instance ID at the document level
            bool_query.must(nested_query.dsl)  # Add the nested query

            # Set the entire bool query to the main query object
            main_query.add_query(bool_query.dsl)

            response = main_query.search(index=RESOURCES_INDEX)
            geometries = []
            for hit in response["hits"]["hits"]:
                if len(geometries) > 0:
                    break
                for geom in hit["_source"]["geometries"]:
                    if len(geometries) > 0:
                        break
                    for feature in geom["geom"]["features"]:
                        if len(geometries) > 0:
                            break
                        if feature["id"] == spatial_filter["featureid"]:
                            geometries.append(feature)

            if len(geometries) > 0:
                feature_geom = geometries[0]["geometry"]
                buffered_feature_geom = add_geoshape_query_to_search_query(
                    feature_geom,
                    spatial_filter,
                    permitted_nodegroups,
                    include_provisional,
                    search_query,
                )

                if include_provisional is False:
                    spatial_query.filter(
                        Terms(field="geometries.provisional", terms=["false"])
                    )

                elif include_provisional == "only provisional":
                    spatial_query.filter(
                        Terms(field="geometries.provisional", terms=["true"])
                    )

                search_query.filter(Nested(path="geometries", query=spatial_query))

        search_query_object["query"].add_query(search_query)

        if self.componentname not in search_query_object:
            search_query_object[self.componentname] = {}

        try:
            search_query_object[self.componentname]["search_buffer"] = feature_geom
        except NameError:
            logger.info(_("Feature geometry is not defined"))


def _buffer(geojson, width=0, unit="ft"):
    geojson = JSONSerializer().serialize(geojson)
    geom = GEOSGeometry(geojson, srid=4326)

    try:
        width = float(width)
    except Exception:
        width = 0

    if width > 0:
        if unit == "ft":
            width = width / 3.28084
        with connection.cursor() as cursor:
            # Transform geom to the analysis SRID, buffer it, and transform it back to wgs84
            cursor.execute(
                """SELECT ST_TRANSFORM(
                    ST_BUFFER(ST_TRANSFORM(ST_SETSRID(%s::geometry, 4326), %s), %s),
                4326)""",
                (
                    geom.hex.decode("utf-8"),
                    settings.ANALYSIS_COORDINATE_SYSTEM_SRID,
                    width,
                ),
            )
            res = cursor.fetchone()
            geom = GEOSGeometry(res[0], srid=4326)
    return geom


def add_geoshape_query_to_search_query(
    feature_geom,
    feature_properties,
    permitted_nodegroups,
    include_provisional,
    search_query,
):

    buffer = {"width": 0, "unit": "ft"}
    if "buffer" in feature_properties:
        buffer = feature_properties["buffer"]
    # feature_geom = spatial_filter["features"][0]["geometry"]
    search_buffer = _buffer(feature_geom, int(buffer["width"]), buffer["unit"])
    feature_geom = JSONDeserializer().deserialize(search_buffer.geojson)
    geoshape = GeoShape(
        field="geometries.geom.features.geometry",
        type=feature_geom["type"],
        coordinates=feature_geom["coordinates"],
    )
    invert_spatial_search = False
    if "inverted" in feature_properties:
        invert_spatial_search = feature_properties["inverted"]

    spatial_query = Bool()
    if invert_spatial_search is True:
        spatial_query.must_not(geoshape)
    else:
        spatial_query.filter(geoshape)

    # get the nodegroup_ids that the user has permission to search
    spatial_query.filter(
        Terms(field="geometries.nodegroup_id", terms=permitted_nodegroups)
    )

    if include_provisional is False:
        spatial_query.filter(Terms(field="geometries.provisional", terms=["false"]))

    elif include_provisional == "only provisional":
        spatial_query.filter(Terms(field="geometries.provisional", terms=["true"]))

    search_query.filter(Nested(path="geometries", query=spatial_query))

    return feature_geom
