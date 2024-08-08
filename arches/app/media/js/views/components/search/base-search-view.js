define([
    'jquery',
    'underscore',
    'knockout',
    'backbone',
    'arches',
    'viewmodels/alert',
], function($, _, ko, BackBone, arches, AlertViewModel) {
    return Backbone.View.extend({
        constructor: function() {
            this.name = 'Base Search View';
            this.filter = {};
            this.requiredFilters = [];
            Backbone.View.apply(this, arguments);
        },

        initialize: function(sharedStateObject) {
            const self = this;
            $.extend(this, sharedStateObject);
            this.requiredFilters = this.getRequiredFilters(this.componentName);
            this.requiredFiltersLoaded = ko.computed(function() {
                let res = true;
                Object.entries(this.searchComponentVms).forEach(function([componentName, filter]) {
                    res = res && filter !== null;
                });
                return res;
            }, this);

            this.query = sharedStateObject.query;
            this.queryString = sharedStateObject.queryString;
            this.defaultQuery = {};
            this.updateRequest = sharedStateObject.updateRequest;
            this.userIsReviewer = sharedStateObject.userIsReviewer;
            this.total = sharedStateObject.total;
            this.userid = sharedStateObject.userid;
            this.hits = sharedStateObject.hits;
            this.alert = sharedStateObject.alert;
            this.sharedStateObject = sharedStateObject;
            this.queryString.subscribe(function() {
                if (this.requiredFiltersLoaded()) {
                    this.doQuery();
                } else {
                    this.requiredFiltersLoaded.subscribe(function() {
                        this.doQuery();
                    }, this);
                }
            }, this);
            // init query
            if (self.updateRequest === undefined) {
                if (this.requiredFiltersLoaded()) {
                    this.doQuery();
                } else {
                    this.requiredFiltersLoaded.subscribe(function() {
                        this.doQuery();
                    }, this);
                }
            }
        },

        doQuery: function() {
            const queryObj = JSON.parse(this.queryString());
            if (self.updateRequest) { self.updateRequest.abort(); }
            self.updateRequest = $.ajax({
                type: "GET",
                url: arches.urls.search_results,
                data: queryObj,
                context: this,
                success: function(response) {
                    _.each(this.sharedStateObject.searchResults, function(value, key, results) {
                        if (key !== 'timestamp') {
                            delete this.sharedStateObject.searchResults[key];
                        }
                    }, this);
                    _.each(response, function(value, key, response) {
                        if (key !== 'timestamp') {
                            this.sharedStateObject.searchResults[key] = value;
                        }
                    }, this);
                    this.sharedStateObject.searchResults.timestamp(response.timestamp);
                    this.sharedStateObject.userIsReviewer(response.reviewer);
                    this.sharedStateObject.userid(response.userid);
                    this.sharedStateObject.total(response.total_results);
                    this.sharedStateObject.hits(response.results.hits.hits.length);
                    this.sharedStateObject.alert(false);
                },
                error: function(response, status, error) {
                    const alert = new AlertViewModel('ep-alert-red', arches.translations.requestFailed.title, response.responseJSON?.message);
                    if(self.updateRequest.statusText !== 'abort'){
                        self.alert(alert);
                    }
                    this.sharedStateObject.loading(false);
                },
                complete: function(request, status) {
                    self.updateRequest = undefined;
                    window.history.pushState({}, '', '?' + $.param(queryObj).split('+').join('%20'));
                    this.sharedStateObject.loading(false);
                }
            });
        },

        getFilter: function(filterName) {
            return ko.unwrap(this.searchComponentVms[filterName]);
        },

        clearQuery: function(){
            Object.values(this.searchComponentVms).forEach(function(value){
                if (value()){
                    if (value().clear){
                        value().clear();
                    }
                }
            }, this);
            this.query(this.defaultQuery);
        },
    });
});