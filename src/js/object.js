"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope, $sce) {
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

    /**
     * Returns an array of objects in the 'dict' of 'type'.
     */
    $scope.get = function (type) {
      var dict = $scope.obj ? $scope.obj.dict : {}
      var result = []
      for (var name in dict) {
        var obj = dict[name]
        if (obj.type == type && ! obj.is_import)
          result.push(obj)
      }
      return result
    }

    /**
     * Returns true iff the 'dict' has any elements of 'type'.
     */
    $scope.has = function (type) {
      return $scope.get(type).length > 0
    }

    // FIXME: Abstract out this filtering with above.
    $scope.getImports = function () {
      var result = {}
      var dict = $scope.module ? $scope.module.dict : {}
      for (var name in dict) {
        var obj = dict[name]
        if (obj.is_import)
          result[name] = obj
      }
      return result
    }

    $scope.formatParameters = function (parameters) {
      return '(' 
        + parameters.map(function (p) { 
          return "<parameter>" + p.name + "</parameter>"
        }).join(', ') 
        + ')'
    }

    // Returns source lines of the displayed object.
    $scope.getSource = function () {
        var sourceLines = $scope.api && $scope.api.source ? $scope.api.source : []
        var source = ''
        for (var i = 0; i < sourceLines.length; ++i) 
            source = source + sourceLines[i]
        return source
    }

    $scope.getDoc = function () { 
      // FIXME: Allow SCE to do some sort of validation here?
      return $sce.trustAsHtml($scope.module.doc) 
    }

  })

