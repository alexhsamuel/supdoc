"use strict"

var App = angular.module('App', ['ngRoute', 'Routing', 'Object'])

App.controller(
	'DocController',
	function ($scope, $http) {
	    $scope.doc = {}

        console.log('about to http get')
	    $http.get('apidoc.json').success(
            function (result) {
                console.log('http get success')
	            $scope.doc = result
	        })

        function getModuleFqnames(doc) {
            var result = []
            for (var name in doc.modules) {
                var submodule = doc.modules[name]
                result.push(submodule.fqname)
                result = result.concat(getModuleFqnames(submodule))
            }
            return result
        }

        $scope.getModuleFqnames = function () {
            console.log('getModuleFqnames')
            return getModuleFqnames($scope.doc)
        }

        $scope.getDoc = function (fqname) {
            var names = fqname.split('.')
            var result = $scope.doc
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

App.controller(
  'NavigationController', 
  function ($scope, $routeParams) {
    $scope.fqname = $routeParams.fqname ? $routeParams.fqname.split('/').join('.') : ''
    $scope.templateUrl = $routeParams.templateUrl
    $scope.$watch(
      function () { return $routeParams.fqname },
      function (fqname) { console.log(fqname) })
  })

