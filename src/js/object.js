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
        $scope.submoduleNames = 
        api && api.modules 
        ? mapObjToArr(api.modules, function (_, m) { return m.fqname })
        : []
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

    $scope.formatParameters = function (parameters) {
      var result = "("
        var first = true
        for (var i = 0; i < parameters.length; ++i) {
          var param = parameters[i]
          if (first) 
            first = false
          else
            result += ", "
          result += param.name
        }
        result += ")"
        return result
      }

  })

