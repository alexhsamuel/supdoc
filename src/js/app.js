"use strict"

var App = angular.module('App', ['ngRoute', 'ObjectModule'])

App.config(
  function ($locationProvider, $routeProvider) {
    $locationProvider.html5Mode(true)
    $routeProvider
      .when('/apyi', { templateUrl: '/title.html' })
      .when('/apyi/:fullname', { templateUrl: '/module.html' }) 
      .otherwise({ templateUrl: '/error.html' }) 
  })

App.controller(
  'ApiController',
  function ($scope, $http) {
    $scope.id = 'ApiController'

    // Load up all the API data.
    $scope.top = null
    $http.get('/apidoc.json').success(
      function (result) {
        $scope.top = result
      })

    $scope.getModuleFqnames = function () {
      return Object.keys($scope.top.modules)
    }

    $scope.getModule = function (fullname) {
      return $scope.top != null ? $scope.top.modules[fullname] : undefined
    }

    $scope.getApi = function (fqname) { 
      return lookUp($scope.top, fqname) 
    }

  })

App.controller(
  'NavigationController', 
  function ($scope, $location, $routeParams) {
    $scope.id = 'NavigationController'
    
    $scope.$watch(
      'fqname',
      function (fullname) {
        // Fish out the API for the containing module.
        $scope.module = $scope.getModule(fullname)

        // Construct parents.
        $scope.parents = []
        if (fullname)
          fullname.split('.').reduce(
            function (p, n) {
              p.push(p.length > 0 ? p[p.length - 1] + '.' + n : n)
              return p
            },
            $scope.parents)

        // Update the location.
        if (isDefined(fullname))
          $location.path('/apyi/' + fullname)
      })

    $scope.navigateToTop = function () {
      $scope.fqname = ''
    }

    $scope.navigateToModule = function (fullname) {
      if ($scope.getModule(fullname)) {
        console.log("nav: module: " + fullname)
        $scope.fqname = fullname
      }
    }

    $scope.getLastPart = function (fqname) {
      var parts = fqname.split('.')
      return parts[parts.length - 1]
    }

    $scope.getParent = function (fqname) {
      if (fqname) {
        var parts = fqname.split('.')
        return parts.slice(0, parts.length - 1).join('.')
      }
      else
        return null
    }

    // Watch for location changes.  This also initializes fqname.
    $scope.$watch(
      function () { 
        return $routeParams.fullname
      },
      function (fullname) { 
        $scope.fqname = fullname
        console.log("nav: from URI: " + fullname)
      })

  })

//-----------------------------------------------------------------------------
// Directives

App.directive(
  'bsPanel',
  function () {
    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      scope: {
        title: '@title',
        collapsed: '=collapsed'
      },
      link: function (scope) {
        scope.collapseId = ('collapse' + scope.title).replace(/[^\w]/g, '')
      },
      template: 
       '<div class="panel panel-default">\
          <div class="panel-heading">\
            <h3 class="panel-title">\
              <a class="accordion-toggle" ng-class="{collapsed: collapsed}" data-toggle="collapse" href="#{{collapseId}}">\
                {{title}}\
              </a>\
            </h3>\
          </div>\
          <div id="{{collapseId}}" class="panel-collapse collapse" ng-class="{in: ! collapsed}">\
            <div class="panel-body" ng-transclude></div>\
          </div>\
        </div>'
    }
  })

//-----------------------------------------------------------------------------

function isUndefined(obj) {
  return typeof obj === 'undefined'
}

function isDefined(obj) {
  return typeof obj !== 'undefined'
}

function mapObjToArr(obj, fn) {
  return Object.keys(obj).map(function (k) { return fn(k, obj[k]) })
}

//-----------------------------------------------------------------------------

function lookUp(api, fqname) {
  if (api == null)
    return null
  if (isUndefined(fqname) || fqname == '')
    return api
  var names = fqname.split('.')
  for (var i = 0; i < names.length; ++i) {
    var name = names[i]
    if (api.modules && name in api.modules) 
      api = api.modules[name]
    else if (api.dict && name in api.dict) 
      // FIXME: Should we do this only for the last name part?
      api = api.dict[name]
    else
      return null
  }
  return api
}

