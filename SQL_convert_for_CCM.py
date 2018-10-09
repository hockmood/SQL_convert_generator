''' Parses through all files in a folder, extracts headers, and creates an SQL import/convert script.
    Prerequisites:        
        Data files need to be in csv format and need to have the same encoding.
        Fieldnames have to be in the first row.    
        Path can be set in the parameters (without the trailing backslash).
        
    Notes:
        Delimiter, filetype, encoding, and names of the output and the log file can be set below.        
'''
import os
import glob
import pandas as pd

# Parameters
delim = '|'
enc = 'utf_16_be'
filetype = 'csv'
data_dir = r'c:\temp_DATA\Python_Parser\oct_test\delim\delim2\converted'
DD03l_path = r'c:\temp_DATA\Python_Parser\oct_test\DD03L.csv'
out_file_name = 'sql_import_all.sql'
log_file_name = 'sql_log.txt'

# SAP datatypes we want to convert
dates = ['DATS']
decimals = ['DEC', 'CURR', 'QUAN', 'FLTP']


class DataTypeSearcher:
    def __init__(self, path):
        self.path = path        
        self.field_types= pd.DataFrame()
    
    def parse_DD03L(self):
        dd03l = pd.read_csv(self.path, delimiter=delim, header=0, dtype=str, encoding=enc)
        self.field_types = dd03l.loc[:, ['TABNAME', 'FIELDNAME', 'DATATYPE']]
        del dd03l
        
    def get_field_type(self, table_name, field_name):
        dtype = self.field_types[(self.field_types.TABNAME == table_name) & (self.field_types.FIELDNAME == field_name)]['DATATYPE'].values[0]        
        return dtype
    

class ScriptGenerator:
    def __init__(self, file_list, out_file, log_file, separator):
        self.file_list = file_list
        self.output_file = out_file
        self.log_file = log_file
        self.separator = separator
        
    def script_beginning(self):
        self.output_file.write('USE []\nGO\nSET ANSI_NULLS ON\nGO\nSET QUOTED_IDENTIFIER ON\nGO\nCREATE PROCEDURE [dbo].[import_data]\n    @path VARCHAR(MAX)=\'\', -- Path needs to be added with a trailing backslash\n    @extension VARCHAR(4)=\'.'+filetype+'\'\nAS\nBEGIN\n\n')
        return self.output_file
        
    def create_tables(self):
        # Print first message.
        self.output_file.write('PRINT \'---------------------\'\n')
        self.output_file.write('PRINT \'---CREATING TABLES---\'\n')
        self.output_file.write('PRINT \'---------------------\'\n'+'\n'+'\n') 
        
        # Reads through the files and selects only headers, then divides them into column names based on selected separator
        for file in self.file_list:
            temp_file = open(file, 'r', encoding=enc)
                # Take the first line, separate into field names, remove newlines etc.
            column_names = temp_file.readline().split(self.separator)
            column_names[-1] = column_names[-1].strip()
            table = os.path.basename(file[:-4])
                        
            # Produce the SQL statement
            self.output_file.write('\n')
            self.output_file.write('PRINT \'[00_'+table+']\'\n')
            self.output_file.write('IF OBJECT_ID(\'[00_'+table+']\') IS NOT NULL DROP TABLE [00_'+table+']\n')
            self.output_file.write('IF OBJECT_ID(\'[00_'+table+']\') IS NULL CREATE TABLE [00_'+table+'] (\n')
            
            
            # Main conditional. Fields.dates/fields.decimals contain the date/decimal fields to convert.
            for column in column_names:
                
                if '-' in column:
                    join_split = column.split('-')
                    table = join_split[0]
                    column = join_split[1]                    
                
                 # If it's the last column, there shouldn't be a trailing comma.
                if column == column_names[-1]:                    
                    self.output_file.write('    ['+column+'] NVARCHAR(MAX)\n')
                    self.output_file.write(')\n')
                # All other columns except the last one have the trailing comma.    
                else:
                    self.output_file.write('    ['+column+'] NVARCHAR(MAX),\n')                    

            self.output_file.write('\n'+'\n') 
        
        return self.output_file
        
    def generate_insert(self):
        # Print first message.
        self.output_file.write('PRINT \'--------------------------------\'\n')
        self.output_file.write('PRINT \'---INSERTING DATA INTO TABLES---\'\n')
        self.output_file.write('PRINT \'--------------------------------\'\n'+'\n'+'\n')
        self.output_file.write('DECLARE @InsertParam VARCHAR(MAX)\n')
        self.output_file.write('DECLARE @sql VARCHAR(MAX)\n')
        self.output_file.write('DECLARE @count VARCHAR(MAX)\n')
        self.output_file.write('SET @InsertParam = \'(FIRSTROW = 2, FIELDTERMINATOR = \'\''+self.separator+'\'\', ROWTERMINATOR = \'\'\\n\'\', CODEPAGE = \'\'ACP\'\', DATAFILETYPE = \'\'widechar\'\', TABLOCK)\'\n\n')
        
        # Reads through the files and selects only headers, then divides them into column names based on selected separator
        for file in self.file_list:
            table = os.path.basename(file[:-4])
                        
            # Produce the SQL statement
            self.output_file.write('\n')
            self.output_file.write('SET @sql = \'BULK INSERT [00_'+table+'] FROM \'\'\' + @path + \''+table+'\' + @extension + \'\'\' WITH \' + @InsertParam; EXEC (@sql); SELECT @count = COUNT(*) FROM [00_'+table+']; PRINT \'[00_'+table+']: \' + @count + \' lines inserted\'')
        
        self.output_file.write('\n\n')
        return self.output_file     
                
    def generate_converts(self, DD03L):
        # Print first message.
        self.output_file.write('PRINT \'-----------------------\'\n')
        self.output_file.write('PRINT \'---CONVERTING TABLES---\'\n')
        self.output_file.write('PRINT \'-----------------------\'\n'+'\n'+'\n')

        self.log_file.write('SQL FIELD TYPES'+'\n'+'\n')        
        
        # Reads through the files and selects only headers, then divides them into column names based on selected separator
        for file in self.file_list:
            temp_file = open(file, 'r', encoding=enc)
                # Take the first line, separate into field names, remove newlines etc.
            column_names = temp_file.readline().split(self.separator)
            column_names[-1] = column_names[-1].strip()
            table = os.path.basename(file[:-4])
            field_name = ''
            tab_name = table
            
            # Produce the SQL statement
            self.output_file.write('\n')
            self.output_file.write('PRINT \''+table+'\'\n')
            self.output_file.write('IF OBJECT_ID(\'['+table+']\') IS NOT NULL DROP TABLE ['+table+']\n')
            self.output_file.write('SELECT\n')
            self.log_file.write(table+':'+'\n')
            
            # Main conditional. Fields.dates/fields.decimals contain the date/decimal fields to convert.
            for column in column_names:
                field_name = column
                
                # In case it's a join table:
                if '-' in column:
                    join_split = column.split('-')
                    tab_name = join_split[0]
                    field_name = join_split[1]
                
                # Get the datatype from the DD03L table                
                dtype = ''
                try:
                    dtype = DD03L.get_field_type(str(tab_name), str(field_name))
                except:
                    dtype = 'N/A'
                
                # Write the field and file type into the log file
                
                self.log_file.write('Table: '+tab_name+'    Field: '+field_name+' DType: '+dtype+'\n')
                
                # If it's the last column, there shouldn't be a trailing comma.
                if column == column_names[-1]:
                    if dtype in (dates):
                        self.output_file.write('    CASE ['+field_name+'] WHEN \'00000000\' THEN NULL ELSE CONVERT(DATE, ['+field_name+'], 101) END AS ['+tab_name+'_'+field_name+']\n')
                        break
                    elif dtype in (decimals):
                        self.output_file.write('    CASE WHEN CHARINDEX(\'-\', ['+field_name+']) > 0 THEN CONVERT(DECIMAL(15,2), SUBSTRING(['+field_name+'], CHARINDEX(\'-\', ['+field_name+']), LEN(['+field_name+'])) + SUBSTRING(['+field_name+'], 0, CHARINDEX(\'-\', ['+field_name+']))) ELSE CONVERT(DECIMAL(15,2), ['+field_name+']) END AS ['+tab_name+'_'+field_name+']\n')
                        break
                    else:
                        self.output_file.write('    LTRIM(RTRIM(['+field_name+'])) AS ['+tab_name+'_'+field_name+']\n')
                        break
                # All other columns except the last one have the trailing comma.    
                else:
                    if dtype in (dates):
                        self.output_file.write('    CASE ['+field_name+'] WHEN \'00000000\' THEN NULL ELSE CONVERT(DATE, ['+field_name+'], 101) END AS ['+tab_name+'_'+field_name+'],\n')
                    elif dtype in (decimals):
                        self.output_file.write('    CASE WHEN CHARINDEX(\'-\', ['+field_name+']) > 0 THEN CONVERT(DECIMAL(15,2), SUBSTRING(['+field_name+'], CHARINDEX(\'-\', ['+field_name+']), LEN(['+field_name+'])) + SUBSTRING(['+field_name+'], 0, CHARINDEX(\'-\', ['+field_name+']))) ELSE CONVERT(DECIMAL(15,2), ['+field_name+']) END AS ['+tab_name+'_'+field_name+'],\n')
                    else:
                        self.output_file.write('    LTRIM(RTRIM(['+field_name+'])) AS ['+tab_name+'_'+field_name+'],\n')
                        
            self.output_file.write('INTO ['+table+']\n')
            self.output_file.write('FROM [00_'+table+']\n')
            self.output_file.write('\n'+'\n')            
            self.log_file.write('\n'+'\n')
        return self.output_file, self.log_file
    
    def script_end(self):
        self.output_file.write('PRINT\'------------------------------------\'\n')
        self.output_file.write('PRINT\'Data import and conversions finished\'\n')
        self.output_file.write('PRINT\'------------------------------------\'\n')
        self.output_file.write('END')
        
        return self.output_file
    

def main():      
    # Open the output file
    output = open(out_file_name, 'w', encoding='utf_8')
    log = open(log_file_name, 'w', encoding='utf_8')
    
    # Read filenames from the directory you're in
    file_list = []
    for filename in glob.glob(data_dir+'\*.'+filetype):    
        file_list.append(filename)
        
    # Parse the DD03L for fields and data types
    Searcher = DataTypeSearcher(path = DD03l_path)
    Searcher.parse_DD03L()
             
    # Initialize the objects
    SqlScriptGenerator = ScriptGenerator(file_list, output, log, delim)
    
    # Generate SQL script
    SqlScriptGenerator.script_beginning()
    SqlScriptGenerator.create_tables()
    SqlScriptGenerator.generate_insert()
    SqlScriptGenerator.generate_converts(Searcher)
    SqlScriptGenerator.script_end()

    # Close the output files
    output.close()
    log.close()     
    
if __name__ == "__main__":
    main()