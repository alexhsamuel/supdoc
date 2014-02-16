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
  'NavigationController', 
  function ($scope, $location, $routeParams) {
    $scope.nav = {
      fqname: $routeParams.fqname || '',
      templateUrl: $routeParams.templateUrl
    }

    $scope.$watch(
      function () { 
        return $routeParams.fqname 
      },
      function (fqname) { 
        console.log(fqname)
        $scope.nav.fqname = fqname 
      })
    $scope.$watch(
      function () { 
        return $scope.nav.fqname 
      },
      function (fqname) { 
        if (typeof fqname !== 'undefined') 
          $location.path('/apyi/' + fqname) 
      })
  })

App.controller(
	'DocController',
	function ($scope, $http) {
	    $scope.api = {}

        console.log('about to http get')
	    $http.get('apidoc.json').success(
            function (result) {
                console.log('http get success')
	            $scope.api = result
	        })

        function getModuleFqnames(api) {
            var result = []
            for (var name in api.modules) {
                var submodule = api.modules[name]
                result.push(submodule.fqname)
                result = result.concat(getModuleFqnames(submodule))
            }
            return result
        }

        $scope.getModuleFqnames = function () {
            console.log('getModuleFqnames')
            return getModuleFqnames($scope.api)
        }

        $scope.getApi = function (fqname) {
            if (isUndefined(fqname) || fqname == '')
                return $scope.api
            var names = fqname.split('.')
            var result = $scope.api
            for (var i = 0; i < names.length; ++i) {
                var name = names[i]
                if (name in result.modules)
                    result = result.modules[name]
                else if (name in result.dict) 
                    // FIXME: Should we do this only for the last name part?
                    result = result.dict[name]
                else
                    return null
            }
            return result
        }
	})

//-----------------------------------------------------------------------------

function isUndefined(obj) {
    return typeof obj === 'undefined'
}