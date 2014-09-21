"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope, $sce) {
    $scope.id = 'ObjectController'

    $scope.showPrivate = false
    $scope.showImported = false
    $scope.showInherited = false
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

    function hasTag(obj, tag) {
      var tags = obj.tags || []
      return tags.some(function (t) { return t == tag })
    }

    function isInherited(obj) { return hasTag(obj, 'inherited'); }
    function isImported(obj) { return hasTag(obj, 'imported'); }

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
      // result.sort()
      return result
    }

    /**
     * Removes a prefix from a dotted identifier, if present.
     */
    $scope.removeNamePrefix = function (name, prefix) {
      console.log('removeNamePrefix(' + name + ', ' + prefix + ')')
      if (name.lastIndexOf(prefix + '.') === 0) 
        return name.substring(prefix.length + 1)
      else
        return name
    }

    /* FIXME: attr.name && (attrname != removeNamePrefix(attr.name, objname)) */
    $scope.showOrigin = function (obj) { return isImported(obj); }

    $scope.showAttr = function (name) {
      var attr = $scope.obj.dict[name]
      var tags = attr.tags || []
      return (
           (tags.indexOf('private')   == -1 || $scope.showPrivate)
        && (tags.indexOf('imported')  == -1 || $scope.showImported)
        && (tags.indexOf('inherited') == -1 || $scope.showInherited)
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

