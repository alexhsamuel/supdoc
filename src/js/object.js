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
        var modname = $scope.module.name
        for (name in $scope.top.modules)
          if (name.length > modname.length
              && name.substr(0, modname.length) == modname) 
            names.push(name)
      }
      return names
    }

    /**
     * Returns names of attributes from the object's 'dict'.
     *
     * @param type
     *   The type of objects to return, or undefined for all.
     * @param is_import
     *   Whether to return imported or defined objects, or undefined for both.
     */
    $scope.getAttrNames = function (type, is_import) {
      var dict = $scope.obj ? $scope.obj.dict : {}
      var result = []
      for (var name in dict) {
        var obj = dict[name]
        if (   (! isDefined(type) || obj.type == type)
            && (! isDefined(is_import) || ! isDefined(obj.is_import) || obj.is_import == is_import))
          result.push(name)
      }
      
      // FIXME: Handle special names?  Handle underscores?
      result.sort()
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

/**
 * Controller for use with 'getAttrNames'.
 *
 *   <span ng-repeat="attrname in getAttrNames(...)" ng-controller="Attrs">
 *     {{attrname}} = {{attr}}
 *   </span>
 */
ObjectModule.controller(
  'Attrs',
  function ($scope) {
    $scope.attr = $scope.obj.dict[$scope.attrname]
  })

