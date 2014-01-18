'use strict'

angular.module('moduleListApp', ['docService']).controller(
  'ModuleListCtrl',
  ['apidocs', function(apidocs) {
    this.module = "foo"
    
    this.moduleNames = ["foo", "bar"]
    var _this = this
    apidocs.load().success(function() { 
      _this.moduleNames = apidocs.getModuleNames() 
    })
    this.dictModules   = function(module) { return apidocs.getItems(module, "module") }
    this.dictFunctions = function(module) { return apidocs.getItems(module, "function") }
    this.dictValues    = function(module) { return apidocs.getItems(module, "values") }
  }])

//------------------------------------------------------------------------------

angular.module('docService', [])
  .factory('apidocs', ['$http', function($http) {
    var modules = {}
    function load() {
      return $http.get('apidoc.json').success(function(data) {
        modules = data
      })
    }
                                      
    function getModuleNames() {
      console.log("getModuleNames")
      return Object.keys(modules)
    }

    function getItems(moduleName, type) {
      console.log("getItems(" + moduleName + ", " + type + ")")
      var module = modules[moduleName]
      if (typeof module === 'undefined')
        return []

      // return (typeof module === 'undefined') ? [] : items(
      //   filterObj(module.dict, function (k, v) { return v.type == type }))

      var result = []
      for (var key in module.dict) {
        var value = module.dict[key]
        if (value.type == type) 
          result.push([key, value])
      }
      return result
    }

    return {
      load              : load,
      getModuleNames    : getModuleNames,
      getItems          : getItems
    }
  }])
