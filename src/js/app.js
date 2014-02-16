"use strict"

var App = angular.module('App', ['ngRoute', 'ObjectModule'])

App.config(
  function ($locationProvider, $routeProvider) {
    $locationProvider.html5Mode(true)
    $routeProvider
      .when('/apyi', { templateUrl: '/title.html' })
      .when('/apyi/:fqname', { templateUrl: '/object.html' }) 
      .otherwise({ templateUrl: '/error.html' }) 
  })

App.controller(
  'ApiController',
  function ($scope, $http) {
    $scope.id = 'ApiController'

    $scope.top = null

    $http.get('/apidoc.json').success(
      function (result) {
        $scope.top = result
      })

    function getModuleFqnames(module) {
      var result = []
      for (var name in module.modules) {
        var submodule = module.modules[name]
        result.push(submodule.fqname)
        result = result.concat(getModuleFqnames(submodule))
      }
      return result
    }

    $scope.getModuleFqnames = function () {
      return getModuleFqnames($scope.top)
    }

    $scope.getApi = function (fqname) { 
      console.log('getApi(' + fqname + ')')
      return lookUp($scope.top, fqname) 
    }

  })

App.controller(
  'NavigationController', 
  function ($scope, $location, $routeParams) {
    $scope.id = 'NavigationController'
    
    $scope.$watch(
      'fqname',
      function (fqname) {
        // Fish out the API for the new object.
        $scope.api = $scope.getApi(fqname)
        // Update the location.
        if (isDefined(fqname))
          $location.path('/apyi/' + fqname)
      })

    $scope.navigateTo = function (fqname) {
      $scope.fqname = fqname
    }

    // Watch for location changes.  This also initializes fqname.
    $scope.$watch(
      function () { 
        return $routeParams.fqname
      },
      function (fqname) { 
        $scope.fqname = fqname 
      })

  })

//-----------------------------------------------------------------------------

function isUndefined(obj) {
  return typeof obj === 'undefined'
}

function isDefined(obj) {
  return typeof obj !== 'undefined'
}

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
