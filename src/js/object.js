"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope) {
  	$scope.id = 'ObjectController'

    /* Names of direct submodules.  */
    $scope.$watch(
      'api',
      function (api) {
        $scope.submoduleNames = api && api.modules ? Object.keys(api.modules) : []
      })

    $scope.getByType = function (type) {
        var result = {}
        var dict = $scope.api ? $scope.api.dict : []
        for (var name in dict) {
            var obj = dict[name]
            if (obj.type == type)
                result[name] = obj
        }
        return result
    }

  })

