"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope, $sce) {
    $scope.id = 'ObjectController'

    $scope.showImported = true
    $scope.showInherited = true
    $scope.showDocs = false

    /**
     * Returns the names of direct submodules.  
     */
    $scope.getSubmodules = function () {
      var modname = $scope.modname

      var subnames = []
      if (modname) 
        for (var i = 0; i < $scope.moduleNames.length; ++i) {
          var name = $scope.moduleNames[i]
          if (name.length > modname.length 
              && name.substr(0, modname.length) == modname) 
            subnames.push(name)
        }
      return subnames
    }

    function isInherited(obj) {
      var tags = obj.tags || []
      return tags.some(function (t) { return t == "inherited" })
    }

    /**
     * Returns names of attributes from the object's 'dict'.
     *
     * @param isInherited
     *   Whether to return inherited or not inherited objets, or undefined
     *   for both.
     */
    $scope.getAttrNames = function (inherited) {
      var dict = $scope.obj ? $scope.obj.dict : {}
      var result = []
      for (var name in dict) {
        var obj = dict[name]
        if ((! defined(inherited) || (isInherited(obj) == inherited)))
          result.push(name)
      }
      
      // FIXME: Handle special names?  Handle underscores?
      result.sort()
      return result
    }

    /**
     * Removes a prefix from a dotted identifier, if present.
     */
    $scope.removeNamePrefix = function (name, prefix) {
      if (name.lastIndexOf(prefix + '.') === 0) 
        return name.substring(prefix.length + 1)
      else
        return name
    }

    $scope.showAttr = function (name) {
      var attr = $scope.obj.dict[name]
      var tags = attr.tags || []
      return (
           (tags.indexOf("imported")  == -1 || $scope.showImported)
        && (tags.indexOf("inherited") == -1 || $scope.showInherited)
        )
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

