"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope, $sce) {
    $scope.id = 'ObjectController'

    /**
      * Returns the names of direct submodules.  
      */
    $scope.getSubmodules = function () {
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
     * Returns objects from the object's 'dict'.
     *
     * @param type
     *   The type of objects to return, or undefined for all.
     * @param is_import
     *   Whether to return imported or defined objects, or undefined for both.
     */
    $scope.get = function (type, is_import) {
      var dict = $scope.obj ? $scope.obj.dict : {}
      var result = []
      for (var name in dict) {
        var obj = dict[name]
        if (   (! isDefined(type) || obj.type == type)
            && (! isDefined(is_import) || obj.is_import == is_import))
          result.push(obj)
      }
      return result
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

