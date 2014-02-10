"use strict"

var moduleListApp = angular.module('moduleListApp', [])

function ApiDocController($scope, $http) {
    function getModuleFqnames(apidoc) {
        var result = []
        for (var name in apidoc.modules) {
            var submodule = apidoc.modules[name]
            result.push(submodule.fqname)
            result = result.concat(getModuleFqnames(submodule))
        }
        return result
    }

    $scope.apidoc = {}
    $scope.moduleName = ""

    $http.get('apidoc.json').success(function (result) {
        $scope.apidoc = result
        $scope.moduleNames = getModuleFqnames($scope.apidoc)
        $scope.moduleName = ''
    })

    $scope.moduleParts = function () {
        if ($scope.moduleName == "")
            return []
        else
            return $scope.moduleName.split(".")
    }

    $scope.module = function () { 
        var parts = $scope.moduleParts()
        var module = $scope.apidoc
        for (var i = 0; i < parts.length; ++i) 
            module = module.modules[parts[i]]
        return module
    }

    $scope.getByType = function (type) {
        var mod = $scope.module()
        var dict = mod ? mod.dict : {}
        var result = {}
        for (var name in dict) {
            var obj = dict[name]
            if (obj.type == type)
                result[name] = obj
        }
        return result
    }

    $scope.getSource = function () {
        var module = $scope.module()
        var sourceLines = module.source
        if (typeof sourceLines === 'undefined')
            return ''
        var source = ""
        for (var i = 0; i < sourceLines.length; ++i) 
            source = source + sourceLines[i]
        return source
    }

    $scope.formatParameters = formatParameters
}


function formatParameters(parameters) {
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

