"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope) {
  	$scope.id = 'ObjectController'

    /* Return names of direct submodules.  */
    $scope.getSubmoduleNames = function () {
      var names = []
      if ($scope.module != null) {
        var moduleName = $scope.module.name
        for (name in $scope.top.modules)
          if (name.length > moduleName.length
              && name.substr(0, moduleName.length) == moduleName) 
            names.push(name)
      }
      return names
    }

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
      return '(' + parameters.map(function (p) { return p.name }).join(', ') + ')'
    }

    // Returns source lines of the displayed object.
    $scope.getSource = function () {
        var sourceLines = $scope.api && $scope.api.source ? $scope.api.source : []
        var source = ''
        for (var i = 0; i < sourceLines.length; ++i) 
            source = source + sourceLines[i]
        return source
    }

  })

