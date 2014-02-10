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
    $scope.fqname = ""

    $http.get('apidoc.json').success(function (result) {
        $scope.apidoc = result
        $scope.moduleNames = getModuleFqnames($scope.apidoc)
        $scope.fqname = ''
    })

    // Returns parts of the fqname of the displayed object.
    $scope.fqnameParts = function () {
        if ($scope.fqname == "")
            return []
        else
            return $scope.fqname.split(".")
    }

    // Returns the displayed object.
    $scope.obj = function () { 
        var parts = $scope.fqnameParts()
        var obj = $scope.apidoc
        for (var i = 0; i < parts.length; ++i) 
            obj = obj.modules[parts[i]]
        return obj
    }

    // Returns source lines of the displayed object.
    $scope.getSource = function () {
        var obj = $scope.obj()
        var sourceLines = obj.source
        if (typeof sourceLines === 'undefined')
            return ''
        var source = ""
        for (var i = 0; i < sourceLines.length; ++i) 
            source = source + sourceLines[i]
        return source
    }

    $scope.getByType = function (type) {
        var mod = $scope.obj()
        var dict = mod ? mod.dict : {}
        var result = {}
        for (var name in dict) {
            var obj = dict[name]
            if (obj.type == type)
                result[name] = obj
        }
        return result
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

